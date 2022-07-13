import os, discord, asyncio
from ...core.interface import Interface
from ...core import Config

class Discordbot(Interface):
    def __init__(self, config, _):
        super(Discordbot, self).__init__()
        config_data = Config(config)

        self.__client = discord.Client()
        self.__channels = {}

        for channel, name in self.channel_names.items():
            if name in config_data.data:
                id, id_given = config_data.get_value_or_default(None, name, 'id')
                if not id_given:
                    print(f'[logfile] WARNING: Channel {name} ignored, since no id is given.')
                    continue
                self.__channels[channel] = Discordbot.Channel(
                    self.__client,
                    id,
                    config_data.get_value_or_default(None, name, 'whitelist')[0],
                    config_data.get_value_or_default(None, name, 'blacklist')[0])

        with open(os.path.join(os.path.dirname(config), config_data.data['token']), "r") as stream:
            self.__token = stream.readline()

    async def start(self):
        asyncio.ensure_future(self.__client.start(self.__token))
        await self.__client.wait_for('ready')
        for channel in self.__channels.values():
            channel.activate()
        channels = ','.join(self.channel_names[x] for x in self.__channels.keys())
        print(f'[discordbot] Discord bot {self.__client.user} ready, available channels: {channels}')

    async def send_message(self, channel, prefix, message):
        if channel not in self.__channels:
            return
        await self.__channels[channel].send(prefix, message)

    class Channel:
        def __init__(self, client, id, whitelist, blacklist):
            self.__client = client
            self.__id = id
            self.__channel = None
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None

        def activate(self):
            self.__channel = self.__client.get_channel(self.__id)

        async def send(self, prefix, message):
            if self.__whitelist is not None and prefix not in self.__whitelist:
                return
            if self.__blacklist is not None and prefix in self.__blacklist:
                return
            message = f'{prefix} {message}'
            max_length = 2000
            size_limited_messages = [message[i:i+max_length] for i in range(0,len(message), max_length)]
            try:
                for sub_message in size_limited_messages:
                    await self.__channel.send(sub_message)
            except:
                print('[discordbot] Failed sending a message.')



