import aiohttp
from datetime import date, timedelta
from ...core import Plugin, Alert, Chiarpc, Config, Balancehistory, Coinprice

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chiawallet', 'name')
        super(Chiawallet, self).__init__(name, outputs)
        self.print(f'Plugin chiawallet; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:9256', 'host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'],
            super(Chiawallet, self), mute_interval)
        self.__wallet_id, _ = config_data.get_value_or_default(1, 'wallet_id')

        self.__wallet_unsynced_alert = Alert(super(Chiawallet, self), mute_interval)

        self.__currency, _ = config_data.get_value_or_default('usd', 'currency')
        self.__history = Balancehistory(config_data.data['history'])
        self.__coinprice = Coinprice('chia', self.__currency)

        self.__yesterday_balance = None
        self.__balance = None

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-startup', self.startup, None)
        scheduler.add_job(f'{name}-dump', self.dump, '55 23 * * *')

    async def startup(self):
        self.__yesterday_balance = self.__history.get_balance(date.today() - timedelta(days=1))
        if self.__yesterday_balance is None:
            self.__yesterday_balance = 0
        self.__balance = self.__yesterday_balance

        await self.check()

    async def check(self):
        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                return
            self.send(Plugin.Channel.debug, f'Wallet balance: {balance} XCH.')
            if balance == self.__balance:
                return
            diff = balance - self.__balance
            self.__balance = balance
            await self.__coinprice.update()
            balance_fiat_string, delta_fiat_string = self.__coinprice.to_fiat_string(self.__balance, diff)
            message = (
                f'Balance changed of wallet {self.__wallet_id}:\n'
                f'delta: {diff} XCH ({delta_fiat_string})\n'
                f'new: {self.__balance} XCH ({balance_fiat_string})'
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
            fiat_string, = self.__coinprice.to_fiat_string(balance)
            self.send(Plugin.Channel.info,
                f'Balance: {balance} XCH ({fiat_string})')

    async def dump(self):
        async with aiohttp.ClientSession() as session:
            balance = await self.__get_balance(session)
            if balance is None:
                return
        delta = balance - self.__yesterday_balance

        await self.__coinprice.update()
        price = self.__coinprice.price
        self.__history.add_balance(date.today(), delta, balance, price)
        self.__yesterday_balance = balance

        fiat_balance = balance * price
        currency = self.__currency.upper()
        message = (
            f'Wallet {self.__wallet_id}: '
            f'{balance:.12f} XCH; '
            f'{price:.4f} {currency}/XCH; '
            f'{fiat_balance:.2f} {currency}\n'
        )
        self.send(Plugin.Channel.report, message)

    async def __get_balance(self, session):
        if not await self.__get_synced(session):
            return None
        json = await self.__rpc.post(session, 'get_wallet_balance', {'wallet_id': self.__wallet_id})
        if json is None:
            return None
        return self.__mojo_to_xch(json['wallet_balance']['confirmed_wallet_balance'])

    async def __get_synced(self, session):
        json = await self.__rpc.post(session, 'get_sync_status')
        if json is None:
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

    def __mojo_to_xch(self, mojo):
        return mojo / 1000000000000.0

