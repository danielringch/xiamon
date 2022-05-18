import os, subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config
from .history import History
from .smartctlparser import SmartctlParser

class Smartctl(Plugin):
    supported__attributes = {
        4: 'Start_Stop_Count',
        5: 'Reallocated_Sectors_Count',
        190: 'Airflow_Temperature_Celsius',
        193: 'Load_Cycle_Count',
        194: 'Temperature_Celsius',
        197: 'Current_Pending_Sector_Count'
    }

    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('smartctl', 'name')
        super(Smartctl, self).__init__(name, outputs)
        self.print(f'Plugin smartctl; name: {name}')

        self.__aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        smartctl_directory = os.path.dirname(config_data.data['binary'])
        smartctl_file = os.path.basename(config_data.data['binary'])
        self.__smartctl_call = os.path.join(smartctl_directory, f'./{smartctl_file}')
        self.__history = History(config_data.data['db'], self.__aggregation) 

        self.__settings = {}
        self.__drives = set()

        global_limits = config_data.data['global_limits']
        self.__settings[None] = Smartctl.Setting(global_limits)
        special_limits, special_limits_available = config_data.get_value_or_default(None, 'drives')
        if special_limits_available:
            for identifier, limits in special_limits.items():
                self.__settings.setdefault(identifier, Smartctl.Setting(global_limits)).load_special_limits(limits)

        self.__mute_interval = self.__aggregation

        self.__offline_alerts = {}
        self.__attribute_alerts = defaultdict(lambda: defaultdict(lambda: Alert(super(Smartctl, self), self.__mute_interval)))

        scheduler.add_job(name ,self.run, config_data.get_value_or_default('0 0 * * *', 'interval')[0])

    async def run(self):
        drives =  self.__get_drives()

        for device in drives:
            parser = self.__get_smart_data(device)
            if not parser.success:
                continue
            if parser.identifier not in self.__drives:
                await self.send(Plugin.Channel.debug, f'Found new drive {parser.identifier}')
            self.__drives.add(parser.identifier)
            settings = self.__settings.get(parser.identifier, self.__settings[None])
            self.__history.update(parser)
            checker = Smartctl.Checker(parser, self.__history, settings, self.__attribute_alerts[parser.identifier])
            await checker.run()

    def __get_drives(self):
        lsblk_output = subprocess.run(["lsblk","-o" , "KNAME"], text=True, stdout=subprocess.PIPE)
        drive_pattern = re.compile("sd\\D+$")
        drives = set()
        for line in lsblk_output.stdout.splitlines():
            device_match = drive_pattern.search(line)
            if not device_match:
                continue
            device = f'/dev/{line}'
            drives.add(device)
        return drives

    def __get_smart_data(self, device):
        output = subprocess.run([self.__smartctl_call,"-iA" , device], text=True, stdout=subprocess.PIPE)
        return SmartctlParser(output.stdout)

    class Setting:
        def __init__(self, global_limits):
            self.start_stop_delta = global_limits['start_stop_delta']
            self.reallocated_sector_delta = global_limits['reallocated_sector_delta']
            self.airflow_temperature_max = global_limits['airflow_temperature_max']
            self.load_cycle_delta = global_limits['load_cycle_delta']
            self.temperature_max = global_limits['temperature_max']
            self.pending_sector_delta = global_limits['pending_sector_delta']

        def load_special_limits(self, limits):
            if 'start_stop_delta' in limits:
                self.start_stop_delta = limits['start_stop_delta']
            if 'reallocated_sector_delta' in limits:
                self.reallocated_sector_delta = limits['reallocated_sector_delta']
            if 'airflow_temperature_max' in limits:
                self.airflow_temperature_max = limits['airflow_temperature_max']
            if 'load_cycle_delta' in limits:
                self.load_cycle_delta = limits['load_cycle_delta']
            if 'temperature_max' in limits:
                self.temperature_max = limits['temperature_max']
            if 'pending_sector_delta' in limits:
                self.pending_sector_delta = limits['pending_sector_delta']

    class Checker:
        def __init__(self, parser, history, settings, alerts):
            self.__parser = parser
            self.__history = history
            self.__settings = settings
            self.__alerts = alerts

        async def run(self):
            await self.__check_delta(self.__parser, self.__history, 4, self.__settings.start_stop_delta)
            await self.__check_delta(self.__parser, self.__history, 5, self.__settings.reallocated_sector_delta)
            await self.__check_max(self.__parser, 190, self.__settings.airflow_temperature_max)
            await self.__check_delta(self.__parser, self.__history, 193, self.__settings.load_cycle_delta)
            await self.__check_max(self.__parser, 194, self.__settings.temperature_max)
            await self.__check_delta(self.__parser, self.__history, 197, self.__settings.pending_sector_delta)

        async def __check_max(self, parser, id, limit):
            if id not in parser.attributes:
                return
            value = parser.attributes[id]
            if value > limit:
                await self.__alerts[id].send(f'Drive {parser.identifier}): attribute {Smartctl.supported__attributes[id]} exceeds maximum value (max={limit} value={value})')

        async def __check_delta(self, parser, history, id, limit):
            if id not in parser.attributes:
                return
            value = parser.attributes[id]
            diff, ref_time = history.get_diff(parser.identifier, id, value)
            if diff is None:
                return
            if diff > limit:
                await self.__alerts[id].send(f'Drive {parser.identifier}: attribute {Smartctl.supported__attributes[id]} exceeds maximum value delta (change={diff}, ref_time={ref_time}')
