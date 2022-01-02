from ssl import SSLContext
from .alert import Alert

class Chiarpc:
    def __init__(self, host, cert, key, plugin, mute_intervall):
        self.__host = host
        self.__context = SSLContext()
        self.__context.load_cert_chain(cert, keyfile=key)
        self.__plugin = plugin
        self.__mute_interval = mute_intervall
        self.__rpc_failed_alerts = {}

    async def post(self, session, cmd, input={}):
        data = {}
        try:
            async with session.post(f'https://{self.__host}/{cmd}', json=input, ssl_context=self.__context) as response:
                response.raise_for_status()
                data = await response.json()
        except Exception as e:
            await self.__handle_connection_error(False, 'exception', cmd, f'Command {cmd}: {str(e)}')
            return None
        if data['success'] != True:
            await self.__handle_connection_error(False, 'nosuccess', cmd, f'Command {cmd} returned no success.')
            return None
        await self.__handle_connection_error(True, None, cmd, None)
        return data

    async def __handle_connection_error(self, success, key, cmd, message):
        if cmd not in self.__rpc_failed_alerts:
            self.__rpc_failed_alerts[cmd] = Alert(self.__plugin, self.__mute_interval)
        alert = self.__rpc_failed_alerts[cmd]
        if success:
            await alert.reset(f'Command {cmd} was successful again.')
        else:
            await alert.send(message, key)
