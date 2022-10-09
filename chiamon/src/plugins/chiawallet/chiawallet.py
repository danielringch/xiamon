import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config, Coinprice, ApiRequestFailedException, Conversions
from .chiawalletdb import Chiawalletdb

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chiawallet', 'name')
        super(Chiawallet, self).__init__(name, outputs)
        self.print(f'Plugin chiawallet; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:9256', 'host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'], super(Chiawallet, self))
        self.__wallet_id, _ = config_data.get_value_or_default(1, 'wallet_id')

        self.__wallet_unsynced_alert = Alert(super(Chiawallet, self), mute_interval)

        self.__db = Chiawalletdb(config_data.data['database'])
        self.__coinprice = Coinprice('chia', config_data.get_value_or_default('usd', 'currency')[0])

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-startup', self.startup, None)
        scheduler.add_job(f'{name}-dump', self.dump, '55 23 * * *')

    async def startup(self):
        if self.__db.balance is None:
            self.send(Plugin.Channel.debug, 'No balance data available in database.')
        else:
            self.send(Plugin.Channel.debug, f'Old balance from database: {self.__db.balance} XCH.')
        await self.check()

    async def check(self):
        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                return
            if self.__db.balance is None:
                self.__db.update_balance(balance, None)
                return
            diff = balance - self.__db.balance
            if diff == 0:
                return
            await self.__coinprice.update()
            self.__db.update_balance(balance, self.__coinprice.price)
            message = (
                f'Balance changed of wallet {self.__wallet_id}:\n'
                f'delta: {diff} XCH ({self.__coinprice.to_fiat_string(diff)})\n'
                f'new: {balance} XCH ({self.__coinprice.to_fiat_string(balance)})'
            )
            self.send(Plugin.Channel.info, message)
            self.send(Plugin.Channel.report, message)

    async def summary(self):
        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                self.send(Plugin.Channel.info, 'Balance unknown, wallet is unavailable.')
                return
            await self.__coinprice.update()
            self.send(Plugin.Channel.info,
                f'Balance: {balance} XCH ({self.__coinprice.to_fiat_string(balance)})')

    async def dump(self):
        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                return

        await self.__coinprice.update()
        price = self.__coinprice.price

        message = (
            f'Wallet {self.__wallet_id}: '
            f'{balance:.12f} XCH; '
            f'{price:.4f} {self.__coinprice.currency}/XCH; '
            f'{self.__coinprice.to_fiat_string(balance)}\n'
        )
        self.send(Plugin.Channel.report, message)

    async def __get_balance(self, session):
        if not await self.__get_synced(session):
            return None
        try:
            json = await self.__rpc.post(session, 'get_wallet_balance', {'wallet_id': self.__wallet_id})
        except ApiRequestFailedException:
            return None
        return Conversions.mojo_to_xch(json['wallet_balance']['confirmed_wallet_balance'])

    async def __get_synced(self, session):
        try:
            json = await self.__rpc.post(session, 'get_sync_status')
        except ApiRequestFailedException:
            return False
        synced = json['synced']
        if not synced:
            if json['syncing']:
                self.__wallet_unsynced_alert.send(f'Wallet is syncing.', 'syncing')
            else:
                self.__wallet_unsynced_alert.send(f'Wallet is not synced.', 'unsynced')
        else:
            self.__wallet_unsynced_alert.reset(f'Wallet is synced again.')
        return synced
