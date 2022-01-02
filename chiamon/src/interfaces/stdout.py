import datetime
from ..core.interface import Interface
from ..core import Config

class Stdout(Interface):
    def __init__(self, config, _):
        super(Stdout, self).__init__()
        config_data = Config(config)

        self.__channels = {}
        self.__formatters = {
            Interface.Channel.alert : self.__alert,
            Interface.Channel.info : self.__info,
            Interface.Channel.error : self.__error,
            Interface.Channel.debug : self.__debug
        }

        for channel, name in self.channel_names.items():
            if name in config_data.data:
                self.__channels[channel] = Stdout.Channel(
                    self.__formatters[channel],
                    config_data.get_value_or_default(None, name, 'whitelist')[0],
                    config_data.get_value_or_default(None, name, 'blacklist')[0])


    async def start(self):
        channels = ','.join(self.channel_names[x] for x in self.__channels.keys())
        print(f'[stdout] Stdout ready, available channels: {channels}')

    async def send_message(self, channel, prefix, message):
        now = datetime.datetime.now()
        self.__channels[channel].send(prefix, message)
        
    def __alert(self, prefix, message):
        return f'[ALERT] [{prefix}] [stdout] [{Stdout.__now()}]', message

    def __info(self, prefix, message):
        return f'[{prefix}] [stdout] [info] [{Stdout.__now()}]', message

    def __error(self, prefix, message):
        return f'[ERROR] [{prefix}] [stdout] [{Stdout.__now()}]', message

    def __debug(self, prefix, message):
        return f'[{prefix}] [stdout] [debug] [{Stdout.__now()}]', message

    @staticmethod
    def __now():
        return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    class Channel:
        def __init__(self, formatter, whitelist, blacklist):
            self.__formatter = formatter
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None

        def send(self, prefix, message):
            prefix, message = self.__formatter(prefix, message)
            self.__print(prefix, message)

        def __print(self, prefix, message):
            lines = message.splitlines()
            print(prefix)
            for line in lines:
                print(f'    {line}')





