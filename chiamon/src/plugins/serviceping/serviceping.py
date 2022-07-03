import aiohttp
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
            chia_checker = Serviceping.Chia(super(Serviceping, self), config_data, mute_interval)
            self.__checkers['chia'] = chia_checker
            self.__alerts['chia'] = Alert(super(Serviceping, self), mute_interval)
        if 'sia' in config_data.data:
            sia_checker = Serviceping.Sia(config_data)
            self.__checkers['sia'] = sia_checker
            self.__alerts['sia'] = Alert(super(Serviceping, self), mute_interval)
        if 'storj' in config_data.data:
            storj_checker = Serviceping.Storj(config_data)
            self.__checkers['storj'] = storj_checker
            self.__alerts['storj'] = Alert(super(Serviceping, self), mute_interval)

        self.__successful_pings = 0
        self.__failed_pings = 0

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        all_online = True
        for name, checker in self.__checkers.items():
            online = await checker.check()
            await self.send(Plugin.Channel.debug, f'Service {name} is {"online" if online else "offline"}.')
            alert  = self.__alerts[name]
            if not online:
                await alert.send(f'Service {name} is offline.')
            else:
                await alert.reset(f'Service {name} is online again.')
            all_online = all_online and online
        if all_online:
            self.__successful_pings += 1
        else:
            self.__failed_pings += 1

    async def summary(self):
        await self.send(Plugin.Channel.info, f'{self.__successful_pings} pings successful, {self.__failed_pings} failed.')
        self.__successful_pings = 0
        self.__failed_pings = 0
        
    class Chia:
        def __init__(self, plugin, config, mute_interval):
            host, _ = config.get_value_or_default('127.0.0.1:8555','chia','host')
            self.__rpc = Chiarpc(host, config.data['chia']['cert'], config.data['chia']['key'],
                plugin, mute_interval)

        async def check(self):
            async with aiohttp.ClientSession() as session:
                response = await self.__rpc.post(session, 'healthz')
                return response is not None

    class Sia:
        def __init__(self, config):
            host, _ = config.get_value_or_default('127.0.0.1:9980', 'sia', 'host')
            password = config.data['sia']['password']
            self.__api = Siaapi(host, password)

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
