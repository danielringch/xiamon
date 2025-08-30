from abc import ABC, abstractmethod
from enum import Enum
from typing import List

class Channel(Enum):
    ALERT = 'alert'
    DEBUG = 'debug'
    ERROR = 'error'
    INFO = 'info'
    ACCOUNTING = 'accounting'
    VERBOSE = 'verbose'

class Interface(ABC):
    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    def send_message(self, channel, prefix, message):
        pass

__interfaces: List[Interface] = []

def add_interface(interface: Interface):
    __interfaces.append(interface)

def send_message(channel: Channel, message: str, sender: str):
    for interface in __interfaces:
        interface.send_message(channel, sender, message)