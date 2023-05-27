from abc import ABC, abstractmethod
from enum import Enum

class Interface(ABC):
    Channel = Enum('Channel', 'alert debug error info accounting verbose')

    def __init__(self):
        self.channel_names = {
            Interface.Channel.alert: 'alert',
            Interface.Channel.debug: 'debug',
            Interface.Channel.error: 'error',
            Interface.Channel.info: 'info',
            Interface.Channel.accounting: 'accounting',
            Interface.Channel.verbose: 'verbose'
        }

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    def send_message(self, channel, prefix, message):
        pass
