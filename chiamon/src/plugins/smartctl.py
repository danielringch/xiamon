import os, subprocess, re, yaml, ciso8601, copy, datetime
from collections import defaultdict
from ..core import Plugin, Alert, Config

__version__ = "0.2.0"

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
        self.print(f'Smartctl plugin {__version__}; name: {name}')

        self.__aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        smartctl_directory = os.path.dirname(config_data.data['binary'])
        smartctl_file = os.path.basename(config_data.data['binary'])
        self.__smartctl_call = os.path.join(smartctl_directory, f'./{smartctl_file}')
        self.__history = Smartctl.History(config_data.data['db'], self.__aggregation) 

        self.__settings = {}
        self.__drives = {}

        global_limits = config_data.data['global_limits']
        self.__settings[None] = Smartctl.Setting(global_limits)
        special_limits, special_limits_available = config_data.get_value_or_default(None, 'drives')
        if special_limits_available:
            for mountpoint, limits in special_limits.items():
                self.__settings.setdefault(mountpoint, Smartctl.Setting(global_limits)).load_special_limits(limits)

        self.__mute_interval = self.__aggregation

        self.__offline_alerts = {}
        self.__attribute_alerts = defaultdict(lambda: defaultdict(lambda: Alert(super(Smartctl, self), self.__mute_interval)))

        scheduler.add_job(name ,self.run, config_data.get_value_or_default('0 0 * * *', 'interval')[0])

    async def run(self):
        raw_drives, all_mounts =  self.__get_drives()
        await self.__update_online_status(all_mounts)

        for device, mounts in raw_drives.items():
            parser = self.__get_smart_data(device)
            if not parser.success:
                continue
            if parser.identifier not in self.__drives:
                await self.send(Plugin.Channel.debug, f'Found new drive {parser.identifier} with mountpoint(s) {";".join(mounts)}')
            self.__drives[parser.identifier] = mounts
            settings = self.__settings[None]
            for mount in mounts:
                if mount in self.__settings:
                    settings = self.__settings[mount]
            self.__history.update(parser)
            checker = Smartctl.Checker(parser, self.__history, settings, self.__attribute_alerts[parser.identifier])
            await checker.run()

    def __get_drives(self):
        lsblk_output = subprocess.run(["lsblk","-o" , "KNAME,MOUNTPOINT"], text=True, stdout=subprocess.PIPE)
        drive_pattern = re.compile("sd\\D+")
        raw_drives = defaultdict(set)
        all_mounts = set()
        for line in lsblk_output.stdout.splitlines():
            parts = re.split("[ \\t]+", line)
            if (len(parts) != 2) or len(parts[1]) == 0:
                continue
            device_match = drive_pattern.search(parts[0])
            if not device_match:
                continue
            device = f'/dev/{device_match.group(0)}'
            mountpoint = parts[1]
            all_mounts.add(mountpoint)
            raw_drives[device].add(mountpoint)
        return raw_drives, all_mounts

    async def __update_online_status(self, all_mounts):
        for identifier, mounts in list(self.__drives.items()):
            online_mounts = mounts.intersection(all_mounts)
            if len(online_mounts) == 0:
                if identifier not in self.__offline_alerts:
                    alert = Alert(super(Smartctl, self), 0)
                    await alert.send(f'Drive {identifier} is offline.')
                    self.__offline_alerts[identifier] = alert
                del self.__drives[identifier]
            else:
                if identifier in self.__offline_alerts:
                    await self.__offline_alerts[identifier].reset(f'Drive {identifier} is online again.')
                    del self.__offline_alerts[identifier]

    def __get_smart_data(self, device):
        output = subprocess.run([self.__smartctl_call,"-iA" , device], text=True, stdout=subprocess.PIPE)
        return Smartctl.Parser(output.stdout)

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

    class Parser:
        def __init__(self, data):
            self.attributes = {}
            self.model = None
            self.serial = None

            header_found = False
            header_regex = re.compile('^ID#.*RAW_VALUE$')
            no_whitespace_regex = re.compile('\\S+')
            id_index = 0
            value_index = None
            for line in data.splitlines():
                if not header_found:
                    if line.startswith('Device Model:     '):
                        self.model = line[18:]
                    elif line.startswith('Serial Number:    '):
                        self.serial = line[18:]
                    elif header_regex.search(line):
                        columns = no_whitespace_regex.findall(line)
                        value_index = len(columns) - 1
                        header_found = True
                elif line:
                    columns = no_whitespace_regex.findall(line)
                    id = int(columns[id_index])
                    try:
                        value = int(columns[value_index])
                        self.attributes[id] = value
                    except ValueError:
                        pass
                else:
                    break

        @property
        def identifier(self):
            if self.model is None or self.serial is None:
                return None
            return f'{self.model}-{self.serial}'

        @property
        def success(self):
            return self.model is not None and self.serial is not None and len(self.attributes) > 0

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

    class History:
        def __init__(self, dir, aggregation):
            self.__file = os.path.join(dir, 'smartdata.yaml')
            try:
                with open(self.__file, "r") as stream:
                    self.__data = yaml.safe_load(stream)
            except FileNotFoundError:
                self.__data = {}
            self.__aggregation = datetime.timedelta(hours=aggregation)

        def update(self, parser):
            drive = parser.identifier
            attributes = parser.attributes
            drive_data = self.__data.setdefault(drive, {})
            if 'timestamp' not in drive_data or \
                ciso8601.parse_datetime(drive_data['timestamp']) + self.__aggregation < datetime.datetime.now():
                drive_data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                drive_data['attributes'] = copy.deepcopy(attributes)
                with open(self.__file, "w") as stream:
                    yaml.safe_dump(self.__data, stream)

        def get_diff(self, drive, id, current_value):
            if drive not in self.__data:
                return None, None
            drive_data = self.__data[drive]
            drive_attributes = drive_data['attributes']
            if id not in drive_attributes:
                print(f'Cache miss for {id}')
                print(drive_data)
                return None, None
            value = drive_attributes[id]
            time_diff = datetime.datetime.now() - ciso8601.parse_datetime(drive_data['timestamp'])
            if time_diff < self.__aggregation:
                return (current_value - value), time_diff
            else:
                scale = time_diff / self.__aggregation
                return ((current_value - value) * scale), time_diff
                
