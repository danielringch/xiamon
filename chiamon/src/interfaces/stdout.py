import datetime
import yaml
from ..core.interface import Interface

class Stdout(Interface):

    __prefix = 'stdout'

    def __init__(self, config):
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__mute_alert = config_data['mute_alert']
            self.__mute_info = config_data['mute_info']
            self.__mute_error = config_data['mute_error']
            self.__mute_debug = config_data['mute_debug']

            self.__channels = {
                Interface.Channel.alert : self.__alert,
                Interface.Channel.info : self.__info,
                Interface.Channel.error : self.__error,
                Interface.Channel.debug : self.__debug
            }

    async def start(self):
        print('[stdout] Stdout ready.')

    async def send_message(self, channel, prefix, message):
        now = datetime.datetime.now()
        self.__channels[channel](f'[stdout] [{prefix}] [{now.strftime("%Y-%m-%dT%H:%M:%S")}]', message)
        
    def __alert(self, prefix, message):
        if self.__mute_alert:
            return
        self.__print(f'[ALERT] {prefix}', message)

    def __info(self, prefix, message):
        if self.__mute_info:
            return
        self.__print(prefix, message)

    def __error(self, prefix, message):
        if self.__mute_error:
            return
        self.__print(f'[ERROR] {prefix}', message)

    def __debug(self, prefix, message):
        if self.__mute_debug:
            return
        self.__print(prefix, message)

    def __print(self, prefix, message):
        lines = message.splitlines()
        print(prefix)
        for line in lines:
            print(f'    {line}')



