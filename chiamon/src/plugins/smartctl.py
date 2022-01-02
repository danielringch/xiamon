import os, subprocess, re, yaml, ciso8601, copy, datetime
from attr import attributes
from typing import DefaultDict
from ..core import Plugin, Alert, Config

__version__ = "0.1.0"

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
        super(Smartctl, self).__init__('smartctl', outputs)
        self.print(f'Smartctl plugin {__version__}')

        config_data = Config(config)

        self.__aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        smartctl_directory = os.path.dirname(config_data.data['binary'])
        smartctl_file = os.path.basename(config_data.data['binary'])
        self.__smartctl_call = call = os.path.join(smartctl_directory, f'./{smartctl_file}')
        self.__history = Smartctl.History(config_data.data['db'], self.__aggregation) 

        self.__drives = {}

        mute_interval = self.__aggregation
        global_limits = config_data.data['global_limits']

        raw_drives = self.__get_drives()
        for device, mounts in raw_drives.items():
            identifier = self.__get_drive_identifier(device)
            if identifier is None:
                self.print(f'Ignoring drive {device}, unable to read model and serial number.')
                continue
            if not self.__check_smart_capability(device):
                self.print(f'Ignoring drive {device}, unable to read attribute values.')
                continue
            drive = Smartctl.Drive(
                plugin=super(Smartctl, self),
                device=device,
                identifier=identifier,
                mounts=mounts,
                global_limits=global_limits,
                mute_intervall=mute_interval)
            drive.load_special_limits(config_data.get_value_or_default(None, 'drives')[0])
            self.__drives[drive.device] = drive
            self.print(f'Found drive {drive.identifier} with mountpoint(s) {";".join(drive.mountpoints)}')

        scheduler.add_job('smartctl' ,self.run, config_data.get_value_or_default('0 0 * * *', 'interval')[0])

    async def run(self):
        for drive in list(self.__drives.values()):
            output = subprocess.run([self.__smartctl_call,"-A" , drive.device], text=True, stdout=subprocess.PIPE)
            parser = Smartctl.Parser(output.stdout)
            if not parser.success():
                await drive.offline_alert.send(f'Drive: {drive.device} ({drive.identifier}) is offline.')
                del self.__drives[drive.device]
                continue
            history = self.__history
            self.__history.update(drive.identifier, parser.attributes)
            await self.__check_delta(drive, parser, history, 4, drive.start_stop_delta)
            await self.__check_delta(drive, parser, history, 5, drive.reallocated_sector_delta)
            await self.__check_max(drive, parser, 190, drive.airflow_temperature_max)
            await self.__check_delta(drive, parser, history, 193, drive.load_cycle_delta)
            await self.__check_max(drive, parser, 194, drive.temperature_max)
            await self.__check_delta(drive, parser, history, 197, drive.pending_sector_delta)

    def __get_drives(self):
        lsblk_output = subprocess.run(["lsblk","-o" , "KNAME,MOUNTPOINT"], text=True, stdout=subprocess.PIPE)
        drive_pattern = re.compile("sd\\D+")
        result = DefaultDict(set)
        for line in lsblk_output.stdout.splitlines():
            parts = re.split("[ \\t]+", line)
            if (len(parts) != 2) or len(parts[1]) == 0:
                continue
            device_match = drive_pattern.search(parts[0])
            if not device_match:
                continue
            device = f'/dev/{device_match.group(0)}'
            mountpoint = parts[1]
            result[device].add(mountpoint)
        return result

    def __check_smart_capability(self, device):
        output = subprocess.run([self.__smartctl_call,"-A" , device], text=True, stdout=subprocess.PIPE)
        return Smartctl.Parser(output.stdout).success()

    def __get_drive_identifier(self, device):
        model = None
        serial = None
        no_whitespace_regex = re.compile('\\S+')
        output = subprocess.run([self.__smartctl_call,"-i" , device], text=True, stdout=subprocess.PIPE)
        for line in output.stdout.splitlines():
            if line.startswith('Device Model:     '):
                model = line[18:]
            elif line.startswith('Serial Number:    '):
                serial = line[18:]
        if model is None or serial is None:
            return None
        return f'{model}-{serial}'

    async def __check_max(self, drive, parser, id, limit):
        if id not in parser.attributes:
            return
        value = parser.attributes[id]
        if value > limit:
            await drive.alerts[id].send(f'Drive: {drive.device} ({drive.identifier}): attribute {Smartctl.supported__attributes[id]} exceeds maximum value (max={limit} value={value})')

    async def __check_delta(self, drive, parser, history, id, limit):
        if id not in parser.attributes:
            return
        value = parser.attributes[id]
        diff, ref_time = history.get_diff(drive.identifier, id, value)
        if diff is None:
            return
        if diff > limit:
            await drive.alerts[id].send(f'Drive: {drive.device} ({drive.identifier}): attribute {Smartctl.supported__attributes[id]} exceeds maximum value delta (change={diff}, ref_time={ref_time}')

    class Drive:
        def __init__(self, plugin, device, identifier, mounts, global_limits, mute_intervall):
            self.__plugin = plugin
            self.device = device
            self.identifier = identifier
            self.mountpoints = set(mounts)
            self.alerts = {id: Alert(plugin, mute_intervall) for id in Smartctl.supported__attributes.keys()}
            self.offline_alert = Alert(plugin, mute_intervall)

            self.start_stop_delta = global_limits['start_stop_delta']
            self.reallocated_sector_delta = global_limits['reallocated_sector_delta']
            self.airflow_temperature_max = global_limits['airflow_temperature_max']
            self.load_cycle_delta = global_limits['load_cycle_delta']
            self.temperature_max = global_limits['temperature_max']
            self.pending_sector_delta = global_limits['pending_sector_delta']

        def load_special_limits(self, special_limits):
            if type(special_limits) is not dict:
                return
            matched = False
            for mountpoint in self.mountpoints:
                if mountpoint not in special_limits:
                    continue
                if matched:
                    self.__plugin.print(f'WARNING: multiple limits for drive {self.device} .')
                    matched = True
                self.__plugin.print(f'Loading deviating limits for {self.device}')
                limits = special_limits[mountpoint]
                self.start_stop_delta = limits['start_stop_delta']
                self.reallocated_sector_delta = limits['reallocated_sector_delta']
                self.airflow_temperature_max = limits['airflow_temperature_max']
                self.load_cycle_delta = limits['load_cycle_delta']
                self.temperature_max = limits['temperature_max']
                self.pending_sector_delta = limits['pending_sector_delta']

    class Parser:
        def __init__(self, data):
            self.attributes = {}

            header_found = False
            header_regex = re.compile('^ID#.*RAW_VALUE$')
            no_whitespace_regex = re.compile('\\S+')
            id_index = 0
            value_index = None
            for line in data.splitlines():
                if not header_found:
                    if header_regex.search(line):
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

        def success(self):
            return len(self.attributes) > 0

    class History:
        def __init__(self, dir, aggregation):
            self.__file = os.path.join(dir, 'smartdata.yaml')
            if os.path.exists(self.__file):
                with open(self.__file, "r") as stream:
                    self.__data = yaml.safe_load(stream)
            else:
                self.__data = {}
            self.__aggregation = datetime.timedelta(hours=aggregation)

        def update(self, drive, attributes):
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
                