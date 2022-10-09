import aiohttp
from collections import defaultdict
from ...core import Plugin, Alert, Config
from ...core import Chiarpc, Siaapi

class Serviceping(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('serviceping', 'name')
        super(Serviceping, self).__init__(name, outputs)
        self.print(f'Plugin serviceping; name: {name}')

        self.__checkers = {}
        self.__alerts = {}
        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        if 'chia' in config_data.data:
            self.__checkers['chia'] = Serviceping.Chia(super(Serviceping, self), config_data, mute_interval)
            self.__alerts['chia'] = Alert(super(Serviceping, self), mute_interval)
        if 'flexfarmer' in config_data.data:
            self.__checkers['flexfarmer'] = Serviceping.Flexfarmer(config_data)
            self.__alerts['flexfarmer'] = Alert(super(Serviceping, self), mute_interval)
        if 'sia' in config_data.data:
            sia_checker = Serviceping.Sia(config_data)
            self.__checkers['sia'] = sia_checker
            self.__alerts['sia'] = Alert(super(Serviceping, self), mute_interval)
        if 'storj' in config_data.data:
            storj_checker = Serviceping.Storj(config_data)
            self.__checkers['storj'] = storj_checker
            self.__alerts['storj'] = Alert(super(Serviceping, self), mute_interval)

        self.__successful_pings = defaultdict(lambda: 0)
        self.__failed_pings = defaultdict(lambda: 0)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        for name, checker in self.__checkers.items():
            online = await checker.check()
            alert  = self.__alerts[name]
            if not online:
                self.__failed_pings[name] += 1
                alert.send(f'Service {name} is offline.')
            else:
                self.__successful_pings[name] += 1
                alert.reset(f'Service {name} is online again.')

    async def summary(self):
        lines = []
        for checker in self.__checkers.keys():
            lines.append(f'{checker}: {self.__successful_pings[checker]} ping successful, {self.__failed_pings[checker]} failed.')
            self.__successful_pings[checker] = 0
            self.__failed_pings[checker] = 0
        self.send(Plugin.Channel.info, '\n'.join(lines))
        
    class Chia:
        def __init__(self, plugin, config, mute_interval):
            host, _ = config.get_value_or_default('127.0.0.1:8555','chia','host')
            self.__rpc = Chiarpc(host, config.data['chia']['cert'], config.data['chia']['key'],
                plugin, mute_interval)

        async def check(self):
            async with aiohttp.ClientSession() as session:
                response = await self.__rpc.post(session, 'healthz')
                return response is not None

    class Flexfarmer:
        def __init__(self, config):
            self.__host, _ = config.get_value_or_default('127.0.0.1:29549','flexfarmer','host')

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f'http://{self.__host}/stats') as response:
                        status = response.status
                        return status >= 200 and status <= 299
                except Exception as e:
                    return False

    class Sia:
        def __init__(self, config):
            host, _ = config.get_value_or_default('127.0.0.1:9980', 'sia', 'host')
            self.__api = Siaapi(host, None)

        async def check(self):
            async with self.__api.create_session() as session:
                try:
                    _ = await self.__api.get(session, 'daemon/version')
                    return True
                except Exception as e:
                    return False

    class Storj:
        def __init__(self, config):
            self.__host, _ = config.get_value_or_default('127.0.0.1:14002', 'storj', 'host')

        async def check(self):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f'http://{self.__host}/static') as response:
                        status = response.status
                        return status >= 200 and status <= 299
                except Exception as e:
                    return False
