from .plugin import Plugin
import datetime

class Alert:
    def __init__(self, plugin, mute_intervall):
        self.__plugin = plugin
        self.__mute_intervall = datetime.timedelta(hours=mute_intervall)
        self.__muted_until = datetime.datetime.fromtimestamp(0)

    async def send(self, message):
        if self.is_muted():
            return
        self.mute()
        await self.__plugin.send(Plugin.Channel.alert, message) 

    async def send_unmute(self, message):
        if not self.is_muted:
            return;
        self.unmute()
        await self.__plugin.send(Plugin.Channel.alert, message) 

    def is_muted(self):
        now = datetime.datetime.now()
        return self.__muted_until > now

    def mute(self):
        if self.__mute_intervall is not None:
            now = datetime.datetime.now()
            self.__muted_until = now + self.__mute_intervall

    def unmute(self):
        self.__muted_until = datetime.datetime.fromtimestamp(0)

class Alerts:
    def __init__(self, plugin):
        self.__plugin = plugin
        self.__alerts = {}

    def add(self, key, alert):
        self.__alerts[key] = alert

    def contains(self, key):
        return key in self.__alerts

    def get(self, key):
        return self.__alerts[key]

    async def send(self, key, message, mute_all=False, unmute_others=False):
        alert = self.__alerts[key]
        if alert.is_muted():
            return
        await alert.send(message)
        if(mute_all):
            for alert in self.__alerts.values():
                alert.mute()
        if(unmute_others):
            self.unmute_all(but=key)

    async def send_unmute(self, message):
        if not self.is_any_muted:
            return;
        self.unmute_all()
        await self.__plugin.send(Plugin.Channel.alert, message) 

    def is_any_muted(self):
        for alert in self.__alerts.values():
            if alert.is_muted():
                return True
        return False

    def unmute_all(self, but=None):
        for alert_key, alert in self.__alerts.items():
            if but != alert_key:
                alert.unmute()

    