from typing import List, Dict
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
        self._channels: Dict[Channel, InstantChannel | AggregatedChannel] = {}
        self.__sender = sender
        self._to_instant_mode()

    def __getitem__(self, channel):
        return self._channels[channel]

    @property
    def alert(self):
        return self._channels[Channel.ALERT]

    @property
    def debug(self):
        return self._channels[Channel.DEBUG]

    @property
    def error(self):
        return self._channels[Channel.ERROR]

    @property
    def info(self):
        return self._channels[Channel.INFO]

    @property
    def accounting(self):
        return self._channels[Channel.ACCOUNTING]

    @property
    def verbose(self):
        return self._channels[Channel.VERBOSE]
    
    def create_aggregator(self):
        return self.Aggregator(self)
    
    def _to_instant_mode(self):
        self._channels[Channel.ALERT] = InstantChannel(self.__sender, Channel.ALERT)
        self._channels[Channel.DEBUG] = InstantChannel(self.__sender, Channel.DEBUG)
        self._channels[Channel.ERROR] = InstantChannel(self.__sender, Channel.ERROR)
        self._channels[Channel.INFO]= InstantChannel(self.__sender, Channel.INFO)
        self._channels[Channel.ACCOUNTING] = InstantChannel(self.__sender, Channel.ACCOUNTING)
        self._channels[Channel.VERBOSE] = InstantChannel(self.__sender, Channel.VERBOSE)

    def _to_aggregated_mode(self):
        self._channels[Channel.ALERT] = AggregatedChannel(Channel.ALERT)
        self._channels[Channel.DEBUG] = AggregatedChannel(Channel.DEBUG)
        self._channels[Channel.ERROR] = AggregatedChannel(Channel.ERROR)
        self._channels[Channel.INFO] = AggregatedChannel(Channel.INFO)
        self._channels[Channel.ACCOUNTING] = AggregatedChannel(Channel.ACCOUNTING)
        self._channels[Channel.VERBOSE] = AggregatedChannel(Channel.VERBOSE)
    
    def _flush(self):
        for channel in self._channels.values():
            channel: AggregatedChannel
            channel.flush(self.__sender)
    
    class Aggregator:
        def __init__(self, message: 'MessageContainer'):
            self.__message = message

        def __enter__(self):
            self.__message._to_aggregated_mode()

        def __exit__(self, exc_type, exc_value, tb):
            self.__message._flush()
            self.__message._to_instant_mode()
