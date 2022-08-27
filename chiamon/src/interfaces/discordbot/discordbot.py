import os, discord, asyncio
from discord.ext import tasks
from queue import Queue
from time import sleep
from threading import Thread
from ...core.interface import Interface
from ...core import Config

class Discordbot(Interface):
    def __init__(self, config, _):
        super(Discordbot, self).__init__()

        config_data = Config(config)

        with open(os.path.join(os.path.dirname(config), config_data.data['token']), "r") as stream:
            token = stream.readline()
        
        self.__worker = Discordbot.DiscordWorker(token, self.channel_names, config_data)
        self.__worker.daemon = True
        

    async def start(self):
        self.__worker.start()
        while not self.__worker.bot.ready:
            sleep(1)
        
        channels = ','.join(self.channel_names[x] for x in self.__worker.bot.channels)
        print(f'[discordbot] Discord bot {self.__worker.bot.user} ready, available channels: {channels}')

    async def send_message(self, channel, sender, message):
        await self.__worker.bot.send_message(channel, sender, message)

    class Channel:
        def __init__(self, client, id, whitelist, blacklist):
            self.__client = client
            self.__id = id
            self.__channel = None
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None
            self.__buffer = Queue(maxsize=100)

        def activate(self):
            self.__channel = self.__client.get_channel(self.__id)

        async def send(self, sender, message):
            if self.__whitelist is not None and sender not in self.__whitelist:
                return
            if self.__blacklist is not None and sender in self.__blacklist:
                return
            message = f'{sender} {message}'
            max_length = 2000
            size_limited_messages = [message[i:i+max_length] for i in range(0,len(message), max_length)]
            for sub_message in size_limited_messages:
                try:
                    self.__buffer.put(item=sub_message, block=False)
                except:
                    print(f'[discordbot] Failed sending a message: send queue overflow.')

        async def flush(self):
            while not self.__buffer.empty():
                try:
                    await self.__channel.send(self.__buffer.get(block=False))
                except Exception as e:
                    print(f'[discordbot] Failed sending a message: {e}.')

    class Bot(discord.Client):
        def __init__(self, channels, config):
            intents = discord.Intents.default()
            intents.messages = True
            intents.message_content = True

            super().__init__(intents=intents)

            self.__channels = {}
            for channel, name in channels.items():
                if name in config.data:
                    id = config.data[name]['id']
                    self.__channels[channel] = Discordbot.Channel(
                        self,
                        id,
                        config.get_value_or_default(None, name, 'whitelist')[0],
                        config.get_value_or_default(None, name, 'blacklist')[0])

            self.__ready = False

        async def setup_hook(self):
            self.flusher.start()

        async def close(self):
            self.flusher.cancel()
            await super().close()

        async def on_ready(self):
            self.__ready = True
            for channel in self.__channels.values():
                channel.activate()

        @tasks.loop(seconds=5)
        async def flusher(self):
            for channel in self.__channels.values():
                await channel.flush()

        @flusher.before_loop
        async def before_flusher(self):
            await self.wait_until_ready()

        async def send_message(self, channel, sender, message):
            if channel not in self.__channels:
                return
            await self.__channels[channel].send(sender, message)

        @property
        def ready(self):
            return self.__ready

        @property
        def channels(self):
            return self.__channels.keys()

    class DiscordWorker(Thread):
        def __init__(self, token, channels, config):
            Thread.__init__(self)
            self.__token = token
            self.__bot = Discordbot.Bot(channels, config)

        async def main(self):
            async with self.__bot:
                await self.__bot.start(self.__token)

        def run(self):
            asyncio.run(self.main())

        @property
        def bot(self):
            return self.__bot



