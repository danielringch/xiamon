import datetime, colorama
from ...core.interface import Interface
from ...core import Config

class Stdout(Interface):
    def __init__(self, config, _):
        super(Stdout, self).__init__()
        config_data = Config(config)

        colorama.init()

        self.__channels = {}

        for channel, name in self.channel_names.items():
            if name in config_data.data:
                self.__channels[channel] = Stdout.Channel(
                    name,
                    config_data.get_value_or_default('reset', name, 'color')[0],
                    config_data.get_value_or_default(None, name, 'whitelist')[0],
                    config_data.get_value_or_default(None, name, 'blacklist')[0])


    async def start(self):
        channels = ','.join(self.channel_names[x] for x in self.__channels.keys())
        print(f'[stdout] Stdout ready, available channels: {channels}')

    async def send_message(self, channel, sender, message):
        if channel not in self.__channels:
            return
        self.__channels[channel].send(sender, message)

    class Channel:
        def __init__(self, prefix, color, whitelist, blacklist):
            self.__colors = {
                'reset' : colorama.Fore.RESET,
                'black' : colorama.Fore.BLACK,
                'red' : colorama.Fore.RED,
                'green' : colorama.Fore.GREEN,
                'yellow' : colorama.Fore.YELLOW,
                'blue' : colorama.Fore.BLUE,
                'magenta' : colorama.Fore.MAGENTA,
                'cyan' : colorama.Fore.CYAN,
                'white' : colorama.Fore.WHITE
            }

            self.__prefix = prefix
            self.__color = color
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None

        @staticmethod
        def __now():
            return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        def send(self, sender, message):
            if self.__whitelist is not None and sender not in self.__whitelist:
                return
            if self.__blacklist is not None and sender in self.__blacklist:
                return
            prefix = f'[{Stdout.Channel.__now()}] [{self.__prefix}] [{sender}]'
            self.__print(prefix, message)

        def __print(self, prefix, message):
            lines = message.splitlines()
            print(self.__colors[self.__color], end='')
            print(f'{prefix} {lines[0]}')
            if len(lines) > 1:
                for line in lines[1:]:
                    print(f'{" " * len(prefix)} {line}')
            print(colorama.Style.RESET_ALL, end='')
