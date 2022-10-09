from abc import ABC
from .interface import Interface

class Plugin(ABC):
    Channel = Interface.Channel

    def __init__(self, name, outputs):
        self.name = name
        self.__outputs = outputs

    def print(self, message):
        lines = message.splitlines()
        if len(lines) == 1:
            print(f'[{self.name}] {message}')
            return
        print(f'[{self.name}]')
        for line in message.splitlines():
            print(f'    {line}')

    def send(self, channel, message):
        for output in self.__outputs:
            output.send_message(channel, self.name, message)
