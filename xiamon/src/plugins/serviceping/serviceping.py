import aiohttp
from collections import defaultdict
from ...core import Plugin
from ...core import Chiarpc, Siaapi, ApiRequestFailedException

class Serviceping(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Serviceping, self).__init__(config, outputs)

        self.__checkers = {}

        ctors = {
            "chia": Serviceping.Chia,
            "sia": Serviceping.Sia,
            "storj": Serviceping.Storj
        }

        for host, config in self.config.data['hosts'].items():
            self.__checkers[host] = ctors[config['type']](config, super(Serviceping, self))

        self.__successful_pings = defaultdict(lambda: 0)
        self.__failed_pings = defaultdict(lambda: 0)

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))

    async def check(self):
        for name, checker in self.__checkers.items():
            online = await checker.check()
            if not online:
                self.__failed_pings[name] += 1
                self.alert(name, f'Service {name} is offline.')
            else:
                self.__successful_pings[name] += 1
                self.reset_alert(name, f'Service {name} is online again.')

    async def summary(self):
        with self.message_aggregator():
            for checker in self.__checkers.keys():
                self.msg.info(f'{checker}: {self.__successful_pings[checker]} ping successful, {self.__failed_pings[checker]} failed.')
                self.__successful_pings[checker] = 0
                self.__failed_pings[checker] = 0
        
    class Chia:
        def __init__(self, config, plugin):
            self.__rpc = Chiarpc(config['host'], config['cert'], config['key'], plugin)

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    await self.__rpc.post(session, 'healthz')
                    return True
                except ApiRequestFailedException:
                    return False

    class Sia:
        def __init__(self, config, plugin):
            self.__api = Siaapi(config['host'], None, plugin)

        async def check(self):
            async with self.__api.create_session() as session:
                try:
                    await self.__api.get(session, 'daemon/version')
                    return True
                except ApiRequestFailedException:
                    return False

    class Storj:
        def __init__(self, config, _):
            self.__host = config['host']

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f'http://{self.__host}/static') as response:
                        status = response.status
                        return status >= 200 and status <= 299
                except Exception as e:
                    return False
