from ...core import Plugin
from .filleddisk import FilledDisk

class Diskfree(Plugin):

    def __init__(self, config, scheduler, outputs):
        super(Diskfree, self).__init__(config, outputs)

        self.__drives = {}

        for drive_block in self.config.data['drives']:
            for path, drive_config in drive_block.items():
                self.__drives[path] = FilledDisk(self, path, drive_config)

        scheduler.add_job(f'{self.name}-check', self.check, self.config.get('0 * * * *', 'check_interval'))

    async def check(self):
        for drive in self.__drives.values():
            drive.check()
