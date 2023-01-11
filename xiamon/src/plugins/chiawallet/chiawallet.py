import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config, Coinprice, ApiRequestFailedException, Conversions
from .chiawalletdb import Chiawalletdb

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('chiawallet', 'name')
        super(Chiawallet, self).__init__(name, outputs)
        self.print(f'Plugin chiawallet; name: {name}')

        mute_interval = config_data.get(24, 'alert_mute_interval')

        host = config_data.get('127.0.0.1:9256', 'host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'], super(Chiawallet, self))
        self.__wallet_id = config_data.get(1, 'wallet_id')

        self.__wallet_unsynced_alert = Alert(super(Chiawallet, self), mute_interval)

        self.__db = Chiawalletdb(config_data.data['database'])
        self.__coinprice = Coinprice('chia', config_data.get('usd', 'currency'))

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get('0 0 * * *', 'summary_interval'))
        scheduler.add_startup_job(f'{name}-startup', self.startup)

    async def startup(self):
        if self.__db.balance is None:
            self.msg.debug('No balance data available in database.')
        else:
            self.msg.debug(f'Old balance from database: {self.__db.balance} XCH.')
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
            self.msg.info(message)
            self.msg.report(message)

    async def summary(self):
        if not await self.__coinprice.update():
            price_message = 'Coin price not available.'
        else:
            price_message = f'Coin price: {self.__coinprice.to_fiat_string(1)}/XCH'

        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                message = f'Balance unknown, wallet is unavailable.\n{price_message}'
            else:
                message = f'Balance: {balance:.12f} XCH ({self.__coinprice.to_fiat_string(balance)})\n{price_message}'

            self.msg.info(message)
            self.msg.report(message)

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
