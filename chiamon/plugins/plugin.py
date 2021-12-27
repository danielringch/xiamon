from abc import ABC, abstractmethod
import asyncio

__version__ = "0.3.0"

class Plugin:
    def __init__(self, prefix, outputs):
        self.__prefix = prefix
        self.__outputs = outputs

    @abstractmethod
    async def run(self):
        pass

    def print(self, message):
        lines = message.splitlines()
        if len(lines) == 1:
            print(f'[{self.__prefix}] {message}')
            return
        print(f'[{self.__prefix}]')
        for line in message.splitlines():
            print(f'    {line}')

    async def send(self, message, is_alert=False):
        sending_tasks = []
        for output in self.__outputs:
            sending_tasks.append(output.send_message(self.__prefix, message, is_alert))

        await asyncio.gather(*sending_tasks)


