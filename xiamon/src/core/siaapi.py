import aiohttp
from .plugin import Plugin
from .exceptions import ApiRequestFailedException

class Siaapi:
    def __init__(self, host, password, plugin):
        self.__host = host
        self.__password = password
        self.__plugin = plugin

    def create_session(self):
        headers = {'User-Agent': 'Sia-Agent'}
        auth = aiohttp.BasicAuth("", self.__password) if self.__password is not None else None
        session = aiohttp.ClientSession(headers=headers, auth=auth)
        return session

    async def get(self, session, cmd, input = {}):
        try:
            parameters = []
            for key, value in input.items():
                parameters.append(f'{key}={value}')
            payload = '?'+'&'.join(parameters) if len(parameters) > 0 else ''
            async with session.get(f'http://{self.__host}/{cmd}{payload}') as response:
                json = await response.json()
                status = response.status
        except Exception as e:
            self.__plugin.msg.debug(f'Command {cmd} failed: {str(e)}')
            raise ApiRequestFailedException()
        if not (status >= 200 and status <= 299):
            self.__plugin.msg.debug(f'Command {cmd} returned status {status}.')
            raise ApiRequestFailedException()
        return json

    async def post(self, session, cmd, input):
        try:
            parameters = []
            for key, value in input.items():
                parameters.append(f'{key}={value}')
            payload = '&'.join(parameters)
            async with session.post(f'http://{self.__host}/{cmd}?{payload}') as response:
                _ = await response.text()
                status = response.status
        except Exception as e:
            self.__plugin.msg.debug(f'Command {cmd} failed: {str(e)}')
            raise ApiRequestFailedException()
        if not (status >= 200 and status <= 299):
            self.__plugin.msg.debug(f'Command {cmd} returned status {status}.')
            raise ApiRequestFailedException()

