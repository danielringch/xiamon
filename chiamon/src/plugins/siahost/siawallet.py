from ...core import Plugin

class Siawallet:
    def __init__(self, plugin, database, coinprice):

        self.__plugin = plugin
        self.__db = database

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

        self.__db.update_balance(free, locked, risked, self.__coinprice.price)

        message = (
            f'Coin price: {self.__coinprice.price} {self.__coinprice.currency}/SC\n'
            f'Balance: {balance} SC ({self.__coinprice.to_fiat_string(balance)})\n'
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)\n'
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)\n'
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)\n'
        )
        self.__plugin.send(Plugin.Channel.report, message)
