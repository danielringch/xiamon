from ssl import SSLContext
from .plugin import Plugin
from .exceptions import ApiRequestFailedException

class Chiarpc:
    def __init__(self, host, cert, key, plugin):
        self.__host = host
        self.__context = SSLContext()
        self.__context.load_cert_chain(cert, keyfile=key)
        self.__plugin = plugin

    async def post(self, session, cmd, input={}):
        data = {}
        try:
            async with session.post(f'https://{self.__host}/{cmd}', json=input, ssl_context=self.__context) as response:
                response.raise_for_status()
                data = await response.json()
        except Exception as e:
            self.__plugin.msg.debug(f'Command {cmd} failed: {str(e)}')
            raise ApiRequestFailedException()
        if data['success'] != True and data['success'] != 'true':
            self.__plugin.msg.debug(f'Command {cmd} returned no success.')
            raise ApiRequestFailedException()
        return data
