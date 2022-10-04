from datetime import date, timedelta
from ...core import Plugin, Balancehistory

class Siawallet:
    def __init__(self, plugin, coinprice, config):

        self.__plugin = plugin

        self.__history = Balancehistory(config.data['history'])
        self.__coinprice = coinprice

    async def summary(self, wallet, locked_collateral, risked_collateral):
        free = round(wallet.balance + wallet.pending)
        locked = round(locked_collateral)
        risked = round(risked_collateral)
        balance = free + locked

        message = (
            f'Balance: {balance} SC ({self.__coinprice.to_fiat_string(balance)})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
        )
        self.__plugin.send(Plugin.Channel.info, message)
            
    async def dump(self, wallet, locked_collateral, risked_collateral):
        free = round(wallet.balance + wallet.pending)
        locked = round(locked_collateral)
        risked = round(risked_collateral)
        balance = free + locked

        message = (
            f'Coin price: {self.__coinprice.price} {self.__coinprice.currency}/SC\n'
            f'Balance: {balance} SC ({self.__coinprice.to_fiat_string(balance)})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
        )
        self.__plugin.send(Plugin.Channel.report, message)

        yesterday_balance = self.__history.get_balance(date.today() - timedelta(days=1))
        if yesterday_balance is None:
            yesterday_balance = 0
        delta = balance - yesterday_balance
        self.__history.add_balance(date.today(), delta, balance, self.__coinprice.price)
