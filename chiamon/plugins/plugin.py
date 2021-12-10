from abc import ABC, abstractmethod

__version__ = "0.1.0"

class Plugin:
    def __init__(self, prefix):
        self.__prefix = prefix

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

