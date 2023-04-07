import aiohttp
from ...core import Plugin, Chiarpc, Coinprice, ApiRequestFailedException, Conversions, CsvExporter
from .chiawalletdb import Chiawalletdb

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chiawallet, self).__init__(config, outputs)

        host = self.config.get('127.0.0.1:9256', 'host')
        self.__rpc = Chiarpc(host, self.config.data['cert'], self.config.data['key'], super(Chiawallet, self))
        self.__wallet_id = self.config.get(1, 'wallet_id')

        self.__db = Chiawalletdb(self.config.data['database'])
        self.__csv = CsvExporter(self.config.get(None, 'csv_export'))
        self.__coinprice = Coinprice('chia', self.config.get('usd', 'currency'))

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        scheduler.add_startup_job(f'{self.name}-startup', self.startup)

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
            self.__csv.add_line({
                'Delta (XCH)': diff,
                f'Delta ({self.__coinprice.currency})': self.__coinprice.to_fiat(diff),
                'New balance (XCH)': balance,
                f'New balance ({self.__coinprice.currency})': self.__coinprice.to_fiat(balance),
                f'Coinprice ({self.__coinprice.currency}/XCH)': self.__coinprice.price
            })
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
                self.alert('unsynced', f'Wallet is syncing.', 'syncing')
            else:
                self.alert('unsynced', f'Wallet is not synced.', 'unsynced')
        else:
            self.reset_alert('unsynced', f'Wallet is synced again.')
        return synced
