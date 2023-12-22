import subprocess, re, json
from collections import defaultdict
from ...core import Plugin, Tablerenderer
from .drive import Drive

class Pingdrive(Plugin):

    def __init__(self, config, scheduler, outputs):
        super(Pingdrive, self).__init__(config, outputs)

        self.__drive_configs = {}
        self.__drives = {}

        for drive_block in self.config.data['drives']:
            for alias, drive_config in drive_block.items():
                drive_config['alias'] = alias
                self.__drive_configs[drive_config['mount_point']] = drive_config
  
        self.__first_summary = True

        scheduler.add_job(f'{self.name}-check', self.check, '* * * * *')
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        scheduler.add_startup_job(f'{self.name}-startup', self.rescan)

    async def check(self):
        for drive in self.__drives.values():
            message = drive.check()
            if message is not None:
                self.msg.debug(message)
            if drive.online:
                self.reset_alert(drive.alias, f'{drive.alias} is online again')
            else:
                self.alert(drive.alias, f'{drive.alias} is offline')

    async def summary(self):
        online = 0
        inactive = 0
        offline = 0
        table = Tablerenderer(['Drive', 'Online', 'Active', 'Expected', 'Pings'])
        for drive in self.__drives.values():
            table.data['Drive'].append(drive.alias)
            table.data['Online'].append(drive.online)
            if not drive.online:
                offline += 1
            else:
                real_active = drive.active_minutes - drive.pings
                table.data['Active'].append(real_active)
                expected_active = drive.expected_active_minutes
                table.data['Expected'].append(expected_active)
                table.data['Pings'].append(drive.pings)
                if not self.__first_summary and real_active < expected_active:
                    self.msg.alert(f'{drive.alias} was too inactive: {real_active}/{expected_active} minutes')
                    inactive += 1
                else:
                    online += 1
            drive.reset_statistics()
        self.msg.verbose(table.render())
        self.msg.info(f'Drives (online, inactive, offline):\n{online} | {inactive} | {offline}')
        self.__first_summary = False

    async def rescan(self):
        for device, mounts in self.__get_drives().items():
            if device not in self.__drives:
                matching_mount = self.__drive_configs.keys() & mounts
                if len(matching_mount) == 0:
                    continue
                if len(matching_mount) > 1:
                    self.msg.error(f'Device {device} has more than one monitored directory, some will be ignored.')
                self.__drives[device] = Drive(device, self.__drive_configs[next(iter(matching_mount))])
                self.msg.debug(f'Added drive {device} ({self.__drives[device].alias}).')

    def __get_drives(self):
        drives = defaultdict(set)
        try:
            output = subprocess.check_output(["findmnt", "--real", "--raw", "--output=source,target", "--noheadings"]).decode("utf-8")
        except subprocess.CalledProcessError as e:
            self.msg.error(f'Can not read drive list: {e}')
            return drives
        
        block_device_pattern = re.compile(r"\/dev\/([a-zA-z0-9]+)")
        drives = defaultdict(set)
        for line in output.splitlines():
            parts = line.split(' ')
            if len(parts) == 2:
                device, mount = parts
                block_device_match = block_device_pattern.search(device)
                if not block_device_match:
                    continue
                block_device = re.sub(r'p?[0-9]+$', '', block_device_match.group(1))
                drives[block_device].add(mount)
        return drives
