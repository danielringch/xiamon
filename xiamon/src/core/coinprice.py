import aiohttp
from enum import Enum

class Coin(Enum):
    CHIA = 'chia'
    SIACOIN = 'siacoin'

class Currency(Enum):
    EUR = 'eur'
    USD = 'usd'

class Coinprice:
    def __init__(self, coin: Coin, currency: Currency):
        self.__coin = coin
        self.__currency = currency
        self.__price: float | None = None

    @property
    def currency(self):
        return self.__currency.value.upper()

    @property
    def price(self):
        return self.__price

    async def update(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.coingecko.com/api/v3/simple/price?ids={self.__coin.value}&vs_currencies={self.__currency.value}') as response:
                    json = await response.json()
                    status = response.status
                    self.__price = json[self.__coin.value][self.__currency.value] if ((status >= 200) and (status <= 299)) else None

        except:
            self.__price = None

        return self.__price is not None

    def to_fiat(self, balance: float, digits: int | None = None):
        if self.__price is None:
            return None
        fiat = balance * self.__price
        return fiat if digits is None else round(fiat, digits)

    def to_fiat_string(self, balance: float, digits: int = 2):
        return f'{self.to_fiat(balance, digits)} {self.currency}'
