import datetime
from ...core import otherdefaultdict
from ...core.interface import Interface
from ...core import Config
from .datesorter import Datesorter
from .pluginsorter import Pluginsorter

class Logfile(Interface):
    def __init__(self, config, scheduler):
        super(Logfile, self).__init__()
        config_data = Config(config)

        self.__date_sorters = otherdefaultdict(lambda x: Datesorter(x))
        self.__plugin_sorters = otherdefaultdict(lambda x: Pluginsorter(x))
        self.__channels = {}

        for channel, name in self.channel_names.items():
            if name in config_data.data:
                file = config_data.get(None, name, 'file')
                if file is None:
                    continue
                sorter = self.__plugin_sorters[file] if config_data.get(False, name, 'sort_by_plugin') else self.__date_sorters[file]
                self.__channels[channel] = Logfile.Channel(
                    name,
                    sorter,
                    config_data.get(None, name, 'whitelist'),
                    config_data.get(None, name, 'blacklist'))

        scheduler.add_job('logfile-flush', self.__flush, "* * * * *")
        scheduler.add_job('logfile-daychange' ,self.__handle_day_change, '0 0 * * *')

    async def start(self):
        channels = ','.join(self.channel_names[x] for x in self.__channels.keys())
        print(f'[logfile] Logfile ready, available channels: {channels}')

    def send_message(self, channel, sender, message):
        if channel not in self.__channels:
            return
        self.__channels[channel].send(sender, message)

    async def __handle_day_change(self):
        for sorter in self.__date_sorters.values():
            sorter.daychange()
        for sorter in self.__plugin_sorters.values():
            sorter.daychange()

    async def __flush(self):
        for sorter in self.__date_sorters.values():
            sorter.flush()
        for sorter in self.__plugin_sorters.values():
            sorter.flush()

    class Channel:
        def __init__(self, name, sorter, whitelist, blacklist):
            self.__sorter = sorter
            self.__name = name
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None
            self.__separator = '|'

        def send(self, sender, raw_message):
            if self.__whitelist is not None and sender not in self.__whitelist:
                return
            if self.__blacklist is not None and sender in self.__blacklist:
                return
            now = self.__now()
            
            message = ''.join(f'{now} | {self.__name} | {sender} {self.__separator} {line}\n' for line in raw_message.splitlines())
            self.__sorter.write(sender, message)
            self.__toggle_separator()

        def __toggle_separator(self):
            self.__separator = '|' if self.__separator == '#' else '#'

        @staticmethod
        def __now():
            return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
