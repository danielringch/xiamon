from abc import ABC, abstractmethod
from enum import Enum
from typing import List

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

__interfaces: List[Interface] = []

def add_interface(interface: Interface):
    __interfaces.append(interface)

def send_message(channel: Interface.Channel, message: str, sender: str):
    for interface in __interfaces:
        interface.send_message(channel, sender, message)