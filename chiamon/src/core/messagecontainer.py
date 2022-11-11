from collections import defaultdict
from .interface import Interface

class MessageContainer:
    def __init__(self, plugin):
        self.__plugin = plugin
        self.__messages = defaultdict(list)

    def __del__(self):
        for channel, lines in self.__messages.items():
            self.__plugin.send(channel, '\n'.join(lines))

    def alert(self, *lines):
        self.__add_lines(Interface.Channel.alert, *lines)

    def info(self, *lines):
        self.__add_lines(Interface.Channel.info, *lines)

    def report(self, *lines):
        self.__add_lines(Interface.Channel.report, *lines)

    def error(self, *lines):
        self.__add_lines(Interface.Channel.error, *lines)

    def debug(self, *lines):
        self.__add_lines(Interface.Channel.debug, *lines)

    def send(self, channel, *lines):
        self.__add_lines(channel, *lines)

    def __add_lines(self, channel, *lines):
        for line in lines:
            if line is not None:
                self.__messages[channel].append(line)

class InstantMessage:
    def __init__(self, plugin):
        self.__plugin = plugin

    def alert(self, *lines):
        self.__add_lines(Interface.Channel.alert, *lines)

    def info(self, *lines):
        self.__add_lines(Interface.Channel.info, *lines)

    def report(self, *lines):
        self.__add_lines(Interface.Channel.report, *lines)

    def error(self, *lines):
        self.__add_lines(Interface.Channel.error, *lines)

    def debug(self, *lines):
        self.__add_lines(Interface.Channel.debug, *lines)

    def send(self, channel, *lines):
        self.__add_lines(channel, *lines)

    def __add_lines(self, channel, *lines):
        self.__plugin.send(channel, '\n'.join(x for x in lines if x is not None))

class MessageAggregator:
    def __init__(self, func):
        self.__func = func

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        self.__func()
