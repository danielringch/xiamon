import aiohttp

class Siaapi:
    def __init__(self, host, password):
        self.__host = host
        self.__password = password

    def create_session(self):
        headers = {'User-Agent': 'Sia-Agent'}
        auth = aiohttp.BasicAuth("", self.__password)
        session = aiohttp.ClientSession(headers=headers, auth=auth)
        return session

    async def get(self, session, cmd, input={}):
        data = {}
        async with session.get(f'http://{self.__host}/{cmd}') as response:
            json = await response.json()
            status = response.status
        if status >= 200 and status <= 299:
            return json
        else:
            raise ConnectionError()
