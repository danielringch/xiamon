from collections import defaultdict
from .interface import Interface

class MessageContainer():
    def __init__(self, alert, info, report, error, debug):
        self.__alert = alert
        self.__info = info
        self.__report = report
        self.__error = error
        self.__debug = debug
        self.__channels = {
            Interface.Channel.alert: self.__alert,
            Interface.Channel.info: self.__info,
            Interface.Channel.report: self.__report,
            Interface.Channel.error: self.__error,
            Interface.Channel.debug: self.__debug
        }

    def __getitem__(self, channel):
        return self.__channels[channel]

    @property
    def alert(self):
        return self.__alert

    @property
    def info(self):
        return self.__info

    @property
    def report(self):
        return self.__report

    @property
    def error(self):
        return self.__error

    @property
    def debug(self):
        return self.__debug

class InstantChannel():
    def __init__(self, plugin, channel):
        self.__plugin = plugin
        self.__channel = channel

    def __call__(self, *lines):
        self.__plugin.send(self.__channel, '\n'.join(x for x in lines if x is not None))

class AggregatedChannel():
    def __init__(self, buffer, channel):
        self.__buffer = buffer
        self.__channel = channel

    def __call__(self, *lines):
        for line in lines:
            if line is not None:
                self.__buffer[self.__channel].append(line)

class AggregatedMessage(MessageContainer):
    def __init__(self, plugin):
        self.__messages = defaultdict(list)
        super(AggregatedMessage, self).__init__(
            AggregatedChannel(self.__messages, Interface.Channel.alert),
            AggregatedChannel(self.__messages, Interface.Channel.info),
            AggregatedChannel(self.__messages, Interface.Channel.report),
            AggregatedChannel(self.__messages, Interface.Channel.error),
            AggregatedChannel(self.__messages, Interface.Channel.debug)
        )
        self.__plugin = plugin

    def flush(self):
        for channel, lines in self.__messages.items():
            self.__plugin.send(channel, '\n'.join(lines))

class InstantMessage(MessageContainer):
    def __init__(self, plugin):
        super(InstantMessage, self).__init__(
            InstantChannel(plugin, Interface.Channel.alert),
            InstantChannel(plugin, Interface.Channel.info),
            InstantChannel(plugin, Interface.Channel.report),
            InstantChannel(plugin, Interface.Channel.error),
            InstantChannel(plugin, Interface.Channel.debug)
        )

class MessageAggregator:
    def __init__(self, func):
        self.__func = func

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        self.__func()
