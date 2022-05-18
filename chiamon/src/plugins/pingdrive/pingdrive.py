import subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config
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
            for drive, drive_config in drive_block.items():
                self.__alerts[drive] = Alert(super(Pingdrive, self), alert_mute_intervall)
                drive_config['alias'] = drive
                self.__drive_configs[drive_config['mount_point']] = drive_config
  
        scheduler.add_job(f'{name}-check', self.check, '* * * * *')
        scheduler.add_job(f'{name}-rescan' ,self.rescan, config_data.get_value_or_default('0 * * * *', 'rescan_intervall')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-startup', self.rescan, None)

    async def check(self):
        messages = {}
        for drive in self.__drives.values():
            messages[drive.alias] = drive.check()
        await self.__merge_message(None, messages)

    async def summary(self):
        messages = {}
        for drive in self.__drives.values():
            pings, active = drive.summary()
            messages[drive.alias] = Plugin.Channel.info, f'{drive.alias}: {pings} pings, {active} active minutes'
        await self.__merge_message('Drive statistics since last summary:', messages)

    async def rescan(self):
        drives = self.__get_drives();
        for device, mounts in drives.items():
            if device not in self.__drives:
                for mount in mounts:
                    if mount in self.__drive_configs:
                        self.__drives[device] = Drive(device, self.__drive_configs[mount])

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

    async def __merge_message(self, prefix, messages):
        channels = defaultdict(lambda: [prefix]) if prefix is not None else defaultdict(lambda: [])
        for drive in sorted(messages):
            channel, message = messages[drive]
            if channel == Plugin.Channel.alert:
                await self.__alerts[drive].send(message)
            else:
                channels[channel].append(message)
        for channel, lines in channels.items():
            await self.send(channel, '\n'.join(lines))
