import datetime

class Alert:
    def __init__(self, plugin, mute_intervall):
        self.__plugin = plugin
        self.__mute_intervall = mute_intervall
        self.__mutes_until = None

    async def send(self, message):
        now = datetime.datetime.now()
        if (self.__mutes_until is not None) and (self.__mutes_until > now):
            return

        if self.__mute_intervall is not None:
            self.__mutes_until = now + self.__mute_intervall

        await self.__plugin.send(message, True)     