import asyncio
from abc import ABC, abstractmethod
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

    async def send(self, channel, message):
        sending_tasks = []
        for output in self.__outputs:
            sending_tasks.append(output.send_message(channel, self.name, message))

        await asyncio.gather(*sending_tasks)
