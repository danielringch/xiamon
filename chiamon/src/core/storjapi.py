import aiohttp
from .plugin import Plugin
from .exceptions import ApiRequestFailedException

class Storjapi:
    def __init__(self, host, plugin):
        self.__host = host
        self.__plugin = plugin

    def create_session(self):
        session = aiohttp.ClientSession()
        return session

    async def get(self, session, cmd):
        try:
            async with session.get(f'http://{self.__host}/api/{cmd}') as response:
                json = await response.json()
                status = response.status
        except Exception as e:
            self.__plugin.send(Plugin.Channel.debug, f'Command {cmd} failed: {str(e)}')
            raise ApiRequestFailedException()
        if not (status >= 200 and status <= 299):
            self.__plugin.send(Plugin.Channel.debug, f'Command {cmd} returned status {status}.')
            raise ApiRequestFailedException()
        return json
