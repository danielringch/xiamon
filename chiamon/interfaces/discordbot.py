import os, discord, yaml, asyncio

class Discordbot:

    __prefix = 'discordbot'

    def __init__(self, config):
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__info_channel = config_data['info_channel']
            self.__alters_channel = config_data['alerts_channel']
        with open(os.path.join(os.path.dirname(config), config_data['token']), "r") as stream:
            self.__token = stream.readline()

        self.__client = discord.Client()

    async def start(self, loop):
        asyncio.ensure_future(self.__client.start(self.__token))
        await self.__client.wait_for('ready')
        self.print(f'Discord bot ready, user {self.__client.user}.')

    async def send_message(self, message, is_alert=False):
        self.print('Sending message:')
        self.print(message, True)
        channel = self.__client.get_channel(self.__alters_channel if is_alert else self.__info_channel)
        await channel.send(message)
        
    def print(self, message, is_subline=False):
        if is_subline:
            for line in message.splitlines():
                print(f'    {line}')
        else:
            for line in message.splitlines():
                print(f'[{self.__prefix}] {line}')



