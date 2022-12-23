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

        self.__plugin.msg.info(
            f'Balance: {balance} SC ({self.__coinprice.to_fiat_string(balance)})',
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)',
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)',
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)'
        )
            
    async def dump(self, wallet, locked_collateral, risked_collateral):
        free = round(wallet.balance + wallet.pending)
        locked = round(locked_collateral)
        risked = round(risked_collateral)
        balance = free + locked

        self.__db.update_balance(free, locked, risked)

        self.__plugin.msg.report(
            f'Coin price: {self.__coinprice.price} {self.__coinprice.currency}/SC',
            f'Balance: {balance} SC ({self.__coinprice.to_fiat_string(balance)})',
            f'Free balance: {free} SC ({(free / balance * 100):.0f} %)',
            f'Locked balance: {locked} SC ({(locked / balance * 100):.0f} %)',
            f'Risked balance: {risked} SC ({(risked / locked * 100):.0f} %)'
        )
