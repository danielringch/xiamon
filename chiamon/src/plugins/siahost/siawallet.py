from datetime import date, timedelta
from urllib.parse import non_hierarchical
from ...core import Plugin, Alert, Siaapi, Siawalletdata, Siahostdata, Config, Balancehistory, Coinprice

class Siawallet:
    def __init__(self, plugin, config):

        self.__plugin = plugin
        mute_interval, _ = config.get_value_or_default(24, 'alert_mute_interval')

        self.__wallet_locked_alert = Alert(super(Siawallet, self), mute_interval)
        self.__low_unlocked_balance_alert = Alert(super(Siawallet, self), mute_interval)

        self.__history = Balancehistory(config.data['history'])
        currency, _ = config.get_value_or_default('usd', 'currency')
        self.__coinprice = Coinprice('siacoin', currency)

    async def check(self, host, wallet):
        wallet_unlocked, free, locked, risked = self.__get_data(host, wallet)
        await self.__check_unlocked(wallet_unlocked)
        await self.__check_balance(free, locked, risked)

    async def summary(self, host, wallet):
        _, free, locked, risked = self.__get_data(host, wallet)
        balance = free + locked
        fiat_string, = await self.__coinprice.to_fiat_string(balance)
        message = (
            f'Balance: {balance} SC ({fiat_string})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
        )
        await self.__plugin.send(Plugin.Channel.info, message)
            
    async def dump(self, host, wallet):
        _, free, locked, _ = self.__get_data(host, wallet)
        balance = free + locked
        yesterday_balance = self.__history.get_balance(date.today() - timedelta(days=1))
        if yesterday_balance is None:
            yesterday_balance = 0
        delta = balance - yesterday_balance
        price = await self.__coinprice.get()
        self.__history.add_balance(date.today(), delta, balance, price)

    async def __check_unlocked(self, unlocked):
        if unlocked:
            await self.__plugin.send(Plugin.Channel.debug, 'Wallet: unlocked.')
            await self.__wallet_locked_alert.reset('Wallet is unlocked again.')
        else:
            await self.__plugin.send(Plugin.Channel.debug, 'Wallet: locked.')
            await self.__wallet_locked_alert.send('Wallet is locked.')

    async def __check_balance(self, free, locked, risked):
        balance = free + locked
        await self.__plugin.send(Plugin.Channel.debug, f'Wallet balance (free/locked/risked): {balance} ({free} / {locked} / {risked}) SC.')
        available_factor = 1.0 - (locked / balance)
        if available_factor < 0.1:
            await self.__low_unlocked_balance_alert.send(f'Non collateral balance is low: {(available_factor * 100):.0f} %')

    def __get_data(self, host, wallet):
        free = wallet.balance + wallet.pending
        locked = host.lockedcollateral
        risked = host.riskedcollateral
        wallet_unlocked = wallet.unlocked
        return wallet_unlocked, int(free), int(locked), int(risked)
