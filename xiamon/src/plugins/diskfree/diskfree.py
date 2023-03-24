
from ...core import Plugin, Config
from .filleddisk import FilledDisk

class Diskfree(Plugin):

    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('diskfree', 'name')
        super(Diskfree, self).__init__(name, outputs)
        self.print(f'Plugin diskfree; name: {name}')

        alert_mute_intervall = config_data.get(24, 'alert_mute_interval')
        self.__drives = {}

        for drive_block in config_data.data['drives']:
            for path, drive_config in drive_block.items():
                self.__drives[path] = FilledDisk(self, path, drive_config, alert_mute_intervall)

        scheduler.add_job(f'{name}-check', self.check, config_data.get('0 * * * *', 'check_interval'))

    async def check(self):
        for drive in self.__drives.values():
            drive.check()
