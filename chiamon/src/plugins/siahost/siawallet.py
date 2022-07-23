from datetime import date, timedelta
from ...core import Plugin, Alert, Balancehistory, Coinprice

class Siawallet:
    def __init__(self, plugin, config):

        self.__plugin = plugin

        self.__history = Balancehistory(config.data['history'])
        currency, _ = config.get_value_or_default('usd', 'currency')
        self.__coinprice = Coinprice('siacoin', currency)

    async def summary(self, host, storage, wallet):
        free = int(wallet.balance + wallet.pending)
        locked = int(host.lockedcollateral)
        risked = int(host.riskedcollateral)
        balance = free + locked
        fiat_string, = await self.__coinprice.to_fiat_string(balance)
        spare_balance_percent = 100 * (free / balance) / (storage.free_space / storage.total_space)
        message = (
            f'Balance: {balance} SC ({fiat_string})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
            f'Free balance vs free space: {spare_balance_percent:.0f} %'
        )
        await self.__plugin.send(Plugin.Channel.info, message)
            
    async def dump(self, host, wallet):
        free = int(wallet.balance + wallet.pending)
        locked = int(host.lockedcollateral)
        risked = int(host.riskedcollateral)
        balance = free + locked

        fiat_string, = await self.__coinprice.to_fiat_string(balance)
        message = (
            f'Balance: {balance} SC ({fiat_string})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
        )
        await self.__plugin.send(Plugin.Channel.report, message)

        yesterday_balance = self.__history.get_balance(date.today() - timedelta(days=1))
        if yesterday_balance is None:
            yesterday_balance = 0
        delta = balance - yesterday_balance
        price = await self.__coinprice.get()
        self.__history.add_balance(date.today(), delta, balance, price)
