from collections import defaultdict
from .interface import Interface

class MessageContainer():
    def __init__(self, alert, debug, error, info, accounting, verbose):
        self.__alert = alert
        self.__debug = debug
        self.__error = error
        self.__info = info
        self.__accounting = accounting
        self.__verbose = verbose
        self.__channels = {
            Interface.Channel.alert: self.__alert,
            Interface.Channel.debug: self.__debug,
            Interface.Channel.error: self.__error,
            Interface.Channel.info: self.__info,
            Interface.Channel.accounting: self.__accounting,
            Interface.Channel.verbose: self.__verbose
        }

    def __getitem__(self, channel):
        return self.__channels[channel]

    @property
    def alert(self):
        return self.__alert

    @property
    def debug(self):
        return self.__debug

    @property
    def error(self):
        return self.__error

    @property
    def info(self):
        return self.__info

    @property
    def accounting(self):
        return self.__accounting

    @property
    def verbose(self):
        return self.__verbose


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
            alert=AggregatedChannel(self.__messages, Interface.Channel.alert),
            debug=AggregatedChannel(self.__messages, Interface.Channel.debug),
            error=AggregatedChannel(self.__messages, Interface.Channel.error),
            info=AggregatedChannel(self.__messages, Interface.Channel.info),
            accounting=AggregatedChannel(self.__messages, Interface.Channel.accounting),
            verbose=AggregatedChannel(self.__messages, Interface.Channel.verbose)
        )
        self.__plugin = plugin

    def flush(self):
        for channel, lines in self.__messages.items():
            self.__plugin.send(channel, '\n'.join(lines))

class InstantMessage(MessageContainer):
    def __init__(self, plugin):
        super(InstantMessage, self).__init__(
            alert=InstantChannel(plugin, Interface.Channel.alert),
            debug=InstantChannel(plugin, Interface.Channel.debug),
            error=InstantChannel(plugin, Interface.Channel.error),
            info=InstantChannel(plugin, Interface.Channel.info),
            accounting=InstantChannel(plugin, Interface.Channel.accounting),
            verbose=InstantChannel(plugin, Interface.Channel.verbose)
        )

class MessageAggregator:
    def __init__(self, func):
        self.__func = func

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        self.__func()
