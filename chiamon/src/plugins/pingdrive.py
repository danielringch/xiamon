import asyncio, glob, random, os
from ..core import Plugin, Alert, Config

__version__ = "0.4.0"

class Pingdrive(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('pingdrive', 'name')
        super(Pingdrive, self).__init__(name, outputs)
        self.print(f'Pingdrive plugin {__version__}; name {name}')

        self.__paths = config_data.data['paths']
        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')
        self.__failed_alerts = {}
        for path in self.__paths:
            self.__failed_alerts[path] = Alert(super(Pingdrive, self), mute_interval)

        scheduler.add_job(name ,self.run, config_data.data['interval'])

    async def run(self):
        ping_tasks = []
        for path in self.__paths:
            ping_tasks.append(self.ping(path))
        await asyncio.gather(*ping_tasks)
        await self.send(Plugin.Channel.debug, 'Pingdrive executed.')

    async def ping(self, path):
        alert = self.__failed_alerts[path]
        try:
            plot_files = glob.glob(os.path.join(path, '*.plot'))
            if(not len(plot_files)):
                raise Exception(f'No plot files in path {path}.')
            plot_file = plot_files[random.randrange(0,len(plot_files))]
            file_size = os.path.getsize(plot_file)
            offset = random.randrange(0, max(file_size - 1024, 1))
            file = open(plot_file, "rb")
            file.seek(offset,0)
            _ = file.read(1024)
            await alert.reset(f'Ping successful again at {path}')
        except:
            await alert.send(f'Ping failed at {path}')
