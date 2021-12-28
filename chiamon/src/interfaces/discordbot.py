import os, discord, yaml, asyncio
from ..core.interface import Interface

class Discordbot:

    __prefix = 'discordbot'

    def __init__(self, config):
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__channels = {
                Interface.Channel.alert : config_data['alert_channel'],
                Interface.Channel.info : config_data['info_channel'],
                Interface.Channel.error : config_data['error_channel'],
                Interface.Channel.debug : config_data['debug_channel']
            }
        with open(os.path.join(os.path.dirname(config), config_data['token']), "r") as stream:
            self.__token = stream.readline()

        self.__client = discord.Client()

    async def start(self):
        asyncio.ensure_future(self.__client.start(self.__token))
        await self.__client.wait_for('ready')
        print(f'[discordbot] Discord bot ready, user {self.__client.user}.')

    async def send_message(self, channel, prefix, message):
        channel_id = self.__channels[channel]
        if channel_id is None:
            return
        discord_channel = self.__client.get_channel(channel_id)
        await discord_channel.send(f'{prefix} {message}')



