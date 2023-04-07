from abc import ABC
from collections import defaultdict
from .interface import Interface
from .messagecontainer import AggregatedMessage, InstantMessage, MessageAggregator
from .config import Config
from .alert import Alert

class Plugin(ABC):
    Channel = Interface.Channel

    def __init__(self, config_file, outputs):
        self.config = Config(config_file)

        self.name = self.config.data['name']

        self.__outputs = outputs
        self.__message_container = None
        self.__instant_message = InstantMessage(self)

        self.__alert_mute_interval = self.config.get(24, 'alert_mute_interval')
        self.__alerts = defaultdict(lambda: Alert(self, self.__alert_mute_interval))

        self.print(f'Plugin {self.__class__.__name__}; name: {self.name}')

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

    def alert(self, key, message, sub_key=None):
        self.__alerts[key].send(message, sub_key)

    def reset_alert(self, key, message):
        self.__alerts[key].reset(message)

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
