import aiohttp

class Storjapi:
    def __init__(self, host):
        self.__host = host

    def create_session(self):
        session = aiohttp.ClientSession()
        return session

    async def get(self, session, cmd):
        data = {}
        async with session.get(f'http://{self.__host}/api/{cmd}') as response:
            json = await response.json()
            status = response.status
        if status >= 200 and status <= 299:
            return json
        else:
            raise ConnectionError()
