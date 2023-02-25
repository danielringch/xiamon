from abc import ABC
from .interface import Interface
from .messagecontainer import AggregatedMessage, InstantMessage, MessageAggregator

class Plugin(ABC):
    Channel = Interface.Channel

    def __init__(self, name, outputs):
        self.name = name
        self.__outputs = outputs
        self.__message_container = None
        self.__instant_message = InstantMessage(self)

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

    @property
    def msg(self):
        if self.__message_container is None:
            return self.__instant_message
        else:
            return self.__message_container

    @property
    def instant(self):
        return self.__instant_message

    def __flush_message_container(self):
        self.__message_container.flush()
        self.__message_container = None

    def message_aggregator(self):
        self.__message_container = AggregatedMessage(self)
        return MessageAggregator(self.__flush_message_container)
