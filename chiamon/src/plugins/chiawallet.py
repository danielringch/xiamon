import aiohttp
from ..core import Plugin, Alert, Chiarpc, Config

__version__ = "0.3.0"

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chiawallet', 'name')
        super(Chiawallet, self).__init__(name, outputs)
        self.print(f'Chiawallet plugin {__version__}; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:9256', 'host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'],
            super(Chiawallet, self), mute_interval)

        self.__wallet_unsynced_alert = Alert(super(Chiawallet, self), mute_interval)

        self.__wallet_id, _ = config_data.get_value_or_default(1, 'wallet_id')
        self.__balance = None

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        await self.send(Plugin.Channel.debug, f'Checking wallet {self.__wallet_id}.')
        async with aiohttp.ClientSession() as session:
            raw_balance = await self.__get_balance(session)
            if raw_balance is None:
                return
            diff = raw_balance - self.__balance if self.__balance is not None else 0
            self.__balance = raw_balance
            if diff != 0:
                await self.send(Plugin.Channel.alert, 
                    (
                        f'Balance changed of wallet {self.__wallet_id}:\n'
                        f'delta: {self.__mojo_to_xch(diff)} XCH\n'
                        f'new: {self.__mojo_to_xch(raw_balance)} XCH'
                    ))

    async def summary(self):
        await self.send(Plugin.Channel.debug, f'Creating summary for wallet {self.__wallet_id} .')
        async with aiohttp.ClientSession() as session:
            raw_balance = await self.__get_balance(session)
            if raw_balance is None:
                return
            await self.send(Plugin.Channel.info,
                f'Wallet balance: {self.__mojo_to_xch(raw_balance)} XCH')

    async def __get_balance(self, session):
        if not await self.__get_synced(session):
            return None
        json = await self.__rpc.post(session, 'get_wallet_balance', {'wallet_id': self.__wallet_id})
        if json is None:
            return None
        return json['wallet_balance']['confirmed_wallet_balance']

    async def __get_synced(self, session):
        json = await self.__rpc.post(session, 'get_sync_status')
        if json is None:
            return False
        synced = json['synced']
        if not synced:
            if json['syncing']:
                await self.__wallet_unsynced_alert.send(f'Wallet is syncing.', 'syncing')
            else:
                await self.__wallet_unsynced_alert.send(f'Wallet is not synced.', 'unsynced')
        else:
            await self.__wallet_unsynced_alert.reset(f'Wallet is synced again.')
        return synced

    def __mojo_to_xch(self, mojo):
        return mojo / 1000000000000.0

