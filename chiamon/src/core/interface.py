from abc import ABC, abstractmethod
from enum import Enum

class Interface(ABC):
    Channel = Enum('Channel', 'alert info report error debug')

    def __init__(self):
        self.channel_names = {
            Interface.Channel.alert: 'alert',
            Interface.Channel.info: 'info',
            Interface.Channel.report: 'report',
            Interface.Channel.error: 'error',
            Interface.Channel.debug: 'debug'
        }

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def send_message(self, channel, prefix, message):
        pass
