from abc import ABC
from collections import defaultdict
from .interface import Interface
from .messagecontainer import MessageContainer
from .config import Config
from .alert import Alert

class Plugin(ABC):
    Channel = Interface.Channel

    def __init__(self, config_file):
        self.config = Config(config_file)

        self.name = self.config.data['name']

        self.__message_container = MessageContainer(self.name)

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

    def alert(self, key, message, sub_key=None):
        self.__alerts[key].send(message, sub_key)

    def reset_alert(self, key, message):
        self.__alerts[key].reset(message)

    @property
    def msg(self):
        return self.__message_container

    def message_aggregator(self):
        return self.__message_container.create_aggregator()
