import aiohttp
from collections import defaultdict
from ...core import Plugin
from ...core import Chiarpc, Siaapi, ApiRequestFailedException

class Serviceping(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Serviceping, self).__init__(config, outputs)

        self.__checkers = {}

        if 'chia' in self.config.data:
            self.__checkers['chia'] = Serviceping.Chia(self.config, super(Serviceping, self))
        if 'flexfarmer' in self.config.data:
            self.__checkers['flexfarmer'] = Serviceping.Flexfarmer(self.config)
        if 'sia' in self.config.data:
            sia_checker = Serviceping.Sia(self.config, super(Serviceping, self))
            self.__checkers['sia'] = sia_checker
        if 'storj' in self.config.data:
            storj_checker = Serviceping.Storj(self.config)
            self.__checkers['storj'] = storj_checker

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
            host = config.get('127.0.0.1:8555','chia','host')
            self.__rpc = Chiarpc(host, config.data['chia']['cert'], config.data['chia']['key'], plugin)

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    await self.__rpc.post(session, 'healthz')
                    return True
                except ApiRequestFailedException:
                    return False

    class Flexfarmer:
        def __init__(self, config):
            self.__host = config.get('127.0.0.1:29549','flexfarmer','host')

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f'http://{self.__host}/stats') as response:
                        status = response.status
                        return status >= 200 and status <= 299
                except Exception:
                    return False

    class Sia:
        def __init__(self, config, plugin):
            host = config.get('127.0.0.1:9980', 'sia', 'host')
            self.__api = Siaapi(host, None, plugin)

        async def check(self):
            async with self.__api.create_session() as session:
                try:
                    await self.__api.get(session, 'daemon/version')
                    return True
                except ApiRequestFailedException:
                    return False

    class Storj:
        def __init__(self, config):
            self.__host = config.get('127.0.0.1:14002', 'storj', 'host')

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f'http://{self.__host}/static') as response:
                        status = response.status
                        return status >= 200 and status <= 299
                except Exception as e:
                    return False
