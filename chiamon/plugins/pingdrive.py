import asyncio, yaml, glob, random, os, datetime
from .plugin import Plugin
from .utils.alert import Alert

__version__ = "0.2.1"

class Pingdrive(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Pingdrive, self).__init__('pingdrive', outputs)
        self.print(f'Pingdrive plugin {__version__}')
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__paths = config_data['paths']

        mute_intervall = config_data['alert_mute_interval']
        self.__ping_failed_alerts = {}
        for path in self.__paths:
            self.__ping_failed_alerts[path] = Alert(super(Pingdrive, self), mute_intervall)

        scheduler.add_job('pingdrive' ,self.run, config_data['intervall'])

    async def run(self):
        ping_tasks = []
        for path in self.__paths:
            ping_tasks.append(self.ping(path))
        await asyncio.gather(*ping_tasks)
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.print(f'{timestamp} Drive ping executed.')

    async def ping(self, path):
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
        except:
            alert = self.__ping_failed_alerts[path]
            await alert.send(f'Ping failed for path: {path}')
