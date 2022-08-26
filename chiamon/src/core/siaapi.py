import aiohttp

class Siaapi:
    def __init__(self, host, password):
        self.__host = host
        self.__password = password

    def create_session(self):
        headers = {'User-Agent': 'Sia-Agent'}
        auth = aiohttp.BasicAuth("", self.__password) if self.__password is not None else None
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

    async def post(self, session, cmd, input):
        parameters = []
        for key, value in input.items():
            parameters.append(f'{key}={value}')
        payload = '&'.join(parameters)
        async with session.post(f'http://{self.__host}/{cmd}?{payload}') as response:
            _ = await response.text()
            status = response.status
        if status >= 200 and status <= 299:
            return
        else:
            raise ConnectionError()

