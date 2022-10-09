import subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config, Tablerenderer
from .drive import Drive

class Pingdrive(Plugin):

    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('pingdrive', 'name')
        super(Pingdrive, self).__init__(name, outputs)
        self.print(f'Plugin pingdrive; name: {name}')

        self.__alerts = {}
        alert_mute_intervall = config_data.get_value_or_default(24, 'alert_mute_interval')[0]
        self.__drive_configs = {}
        self.__drives = {}

        for drive_block in config_data.data['drives']:
            for alias, drive_config in drive_block.items():
                self.__alerts[alias] = Alert(super(Pingdrive, self), alert_mute_intervall)
                drive_config['alias'] = alias
                self.__drive_configs[drive_config['mount_point']] = drive_config
  
        self.__first_summary = True

        scheduler.add_job(f'{name}-check', self.check, '* * * * *')
        scheduler.add_job(f'{name}-rescan' ,self.rescan, config_data.get_value_or_default('0 * * * *', 'rescan_intervall')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-startup', self.rescan, None)

    async def check(self):
        messages = []
        for drive in self.__drives.values():
            message = drive.check()
            if message is not None:
                messages.append(message)
            if drive.online:
                self.__alerts[drive.alias].reset(f'{drive.alias} is online again')
            else:
                self.__alerts[drive.alias].send(f'{drive.alias} is offline')
        if len(messages) > 0:
            self.send(Plugin.Channel.debug, '\n'.join(messages))

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
                    self.send(Plugin.Channel.alert, f'{drive.alias} was too inactive: {real_active}/{expected_active} minutes')
                    inactive += 1
                else:
                    online += 1
            drive.reset_statistics()
        self.send(Plugin.Channel.info, f'Drives (online, inactive, offline):\n{online} | {inactive} | {offline}')
        self.send(Plugin.Channel.report, table.render())
        self.__first_summary = False

    async def rescan(self):
        drives = self.__get_drives();
        # remove old devices
        for device in list(self.__drives.keys()):
            if device not in drives:
                self.send(Plugin.Channel.debug, f'Removed drive {device} ({self.__drives[device].alias}).')
                del self.__drives[device]
        # add new devices
        for device, mounts in drives.items():
            if device not in self.__drives:
                matching_mount = self.__drive_configs.keys() & mounts
                if len(matching_mount) == 0:
                    continue
                if len(matching_mount) > 1:
                    self.send(Plugin.Channel.error, f'Device {device} has more than one monitored directory, some will be ignored.')
                self.__drives[device] = Drive(device, self.__drive_configs[next(iter(matching_mount))])
                self.send(Plugin.Channel.debug, f'Added drive {device} ({self.__drives[device].alias}).')

    def __get_drives(self):
        lsblk_output = subprocess.run(["lsblk","-o" , "KNAME,MOUNTPOINT"], text=True, stdout=subprocess.PIPE)
        drive_pattern = re.compile("sd\\D+")
        drives = defaultdict(set)
        for line in lsblk_output.stdout.splitlines():
            parts = re.split("[ \\t]+", line)
            if (len(parts) != 2) or len(parts[1]) == 0:
                continue
            device_match = drive_pattern.search(parts[0])
            if not device_match:
                continue
            device = device_match.group(0)
            mountpoint = parts[1]
            drives[device].add(mountpoint)
        return drives
