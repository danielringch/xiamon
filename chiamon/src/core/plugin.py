import asyncio
from abc import ABC, abstractmethod
from .interface import Interface

class Plugin(ABC):
    Channel = Interface.Channel

    def __init__(self, prefix, outputs):
        self.__prefix = prefix
        self.__outputs = outputs

    def print(self, message):
        lines = message.splitlines()
        if len(lines) == 1:
            print(f'[{self.__prefix}] {message}')
            return
        print(f'[{self.__prefix}]')
        for line in message.splitlines():
            print(f'    {line}')

    async def send(self, channel, message):
        sending_tasks = []
        for output in self.__outputs:
            sending_tasks.append(output.send_message(channel, self.__prefix, message))

        await asyncio.gather(*sending_tasks)
