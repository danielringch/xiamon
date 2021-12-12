from abc import ABC, abstractmethod
import asyncio

__version__ = "0.2.0"

class Plugin:
    def __init__(self, prefix, outputs):
        self.__prefix = prefix
        self.__outputs = outputs

    @abstractmethod
    async def run(self):
        pass

    def print(self, message, is_subline=False):
        if is_subline:
            for line in message.splitlines():
                print(f'    {line}')
        else:
            for line in message.splitlines():
                print(f'[{self.__prefix}] {line}')

    async def send(self, message, is_alert=False):
        sending_tasks = []
        for output in self.__outputs:
            sending_tasks.append(output.send_message(f'[{self.__prefix}] {message}', is_alert))

        await asyncio.gather(*sending_tasks)


