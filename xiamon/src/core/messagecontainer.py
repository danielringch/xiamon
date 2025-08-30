from typing import List
from .interface import Channel, send_message

class InstantChannel():
    def __init__(self, sender, channel: Channel):
        self.__sender = sender
        self.__channel = channel

    def __call__(self, *lines):
        send_message(self.__channel, '\n'.join(x for x in lines if x), self.__sender)

class AggregatedChannel():
    def __init__(self, channel: Channel):
        self.__buffer: List[str] = []
        self.__channel = channel

    def __call__(self, *lines):
        self.__buffer.extend(x for x in lines if x)

    def flush(self, sender: str):
        send_message(self.__channel, '\n'.join(self.__buffer), sender)

class MessageContainer():
    def __init__(self, sender: str):
        self.__sender = sender
        self.__to_instant_mode()
        self._channels = {
            Channel.ALERT: self._alert,
            Channel.DEBUG: self._debug,
            Channel.ERROR: self._error,
            Channel.INFO: self._info,
            Channel.ACCOUNTING: self._accounting,
            Channel.VERBOSE: self._verbose
        }

    def __getitem__(self, channel):
        return self._channels[channel]

    @property
    def alert(self):
        return self._alert

    @property
    def debug(self):
        return self._debug

    @property
    def error(self):
        return self._error

    @property
    def info(self):
        return self._info

    @property
    def accounting(self):
        return self._accounting

    @property
    def verbose(self):
        return self._verbose
    
    def create_aggregator(self):
        return self.Aggregator(self)
    
    def __to_instant_mode(self):
        self._alert = InstantChannel(self.__sender, Channel.ALERT)
        self._debug = InstantChannel(self.__sender, Channel.DEBUG)
        self._error = InstantChannel(self.__sender, Channel.ERROR)
        self._info = InstantChannel(self.__sender, Channel.INFO)
        self._accounting = InstantChannel(self.__sender, Channel.ACCOUNTING)
        self._verbose = InstantChannel(self.__sender, Channel.VERBOSE)

    def __to_aggregated_mode(self):
        self._alert = AggregatedChannel(Channel.ALERT)
        self._debug = AggregatedChannel(Channel.DEBUG)
        self._error = AggregatedChannel(Channel.ERROR)
        self._info = AggregatedChannel(Channel.INFO)
        self._accounting = AggregatedChannel(Channel.ACCOUNTING)
        self._verbose = AggregatedChannel(Channel.VERBOSE)
    
    def __flush(self):
        for channel in self._channels.values():
            channel: AggregatedChannel
            channel.flush(self.__sender)
    
    class Aggregator:
        def __init__(self, message: 'MessageContainer'):
            self.__message = message

        def __enter__(self):
            self.__message.__to_aggregated_mode()

        def __exit__(self, exc_type, exc_value, tb):
            self.__message.__flush()
            self.__message.__to_instant_mode()
