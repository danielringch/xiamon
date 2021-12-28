from abc import ABC, abstractmethod
from enum import Enum

class Interface(ABC):
    Channel = Enum('Channel', 'alert info error debug')

    def __init__(self):
        pass

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def send_message(self, channel, prefix, message):
        pass
