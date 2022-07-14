from datetime import date, timedelta
from ...core import Plugin, Alert, Siaapi, Siawalletdata, Siahostdata, Config, Balancehistory, Coinprice

class Siawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('siawallet', 'name')
        super(Siawallet, self).__init__(name, outputs)
        self.print(f'Plugin siawallet; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:9980','host')
        self.__api = Siaapi(host, config_data.data['password'])


        self.__request_alert = Alert(super(Siawallet, self), mute_interval)
        self.__wallet_locked_alert = Alert(super(Siawallet, self), mute_interval)
        self.__low_unlocked_balance_alert = Alert(super(Siawallet, self), mute_interval)

        self.__history = Balancehistory(config_data.data['history'])
        currency, _ = config_data.get_value_or_default('usd', 'currency')
        self.__coinprice = Coinprice('siacoin', currency)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-dump', self.dump, '55 23 * * *')

    async def check(self):
        data = await self.__get_data()
        if len(data) == 4:
            wallet_unlocked, free, locked, risked = data
            await self.__check_unlocked(wallet_unlocked)
            await self.__check_balance(free, locked, risked)

    async def summary(self):
        data = await self.__get_data()
        if len(data) == 4:
            _, free, locked, risked = data
            balance = free + locked
            fiat_string, = await self.__coinprice.to_fiat_string(balance)
            message = (
                f'Balance: {balance} SC ({fiat_string})\n'
                f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
                f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
                f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
            )
            await self.send(Plugin.Channel.info, message)
        else:
            await self.send(Plugin.Channel.info, f'Balance: unknown, wallet is unavailable.')

    async def dump(self):
        data = await self.__get_data()
        if len(data) != 4:
            return
        _, free, locked, _ = data
        balance = free + locked
        yesterday_balance = self.__history.get_balance(date.today() - timedelta(days=1))
        if yesterday_balance is None:
            yesterday_balance = 0
        delta = balance - yesterday_balance
        price = await self.__coinprice.get()
        self.__history.add_balance(date.today(), delta, balance, price)

    async def __check_unlocked(self, unlocked):
        if unlocked:
            await self.send(Plugin.Channel.debug, 'Wallet is unlocked.')
            await self.__wallet_locked_alert.reset('Wallet is unlocked again.')
        else:
            await self.send(Plugin.Channel.debug, 'Wallet is locked.')
            await self.__wallet_locked_alert.send('Wallet is locked.')

    async def __check_balance(self, free, locked, risked):
        balance = free + locked
        await self.send(Plugin.Channel.debug, f'Wallet balance (free/locked/risked): {balance} ({free} / {locked} / {risked}) SC.')
        available_factor = 1.0 - (locked / balance)
        if available_factor < 0.1:
            await self.__low_unlocked_balance_alert.send(f'Non collateral balance is low: {(available_factor * 100):.0f} %')

    async def __get_data(self):
        async with self.__api.create_session() as session:
            try:
                wallet_data = Siawalletdata(await self.__api.get(session, 'wallet'))
                host_data = Siahostdata(await self.__api.get(session, 'host'))
                free = wallet_data.balance + wallet_data.pending
                locked = host_data.lockedcollateral
                risked = host_data.riskedcollateral
                wallet_unlocked = wallet_data.unlocked
                await self.__request_alert.reset(f'Requests "wallet" and "host" are successful again.')
                return wallet_unlocked, int(free), int(locked), int(risked)
            except Exception as e:
                await self.__request_alert.send(f'Request "wallet" or "host" failed.')
                return []
