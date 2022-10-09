import aiohttp

class Coinprice:
    def __init__(self, id, currency):
        self.__id = id
        self.__currency = currency
        self.__price = None

    @property
    def currency(self):
        return self.__currency.upper()

    @property
    def price(self):
        return self.__price

    async def update(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.coingecko.com/api/v3/simple/price?ids={self.__id}&vs_currencies={self.__currency}') as response:
                    json = await response.json()
                    status = response.status
                    if status >= 200 and status <= 299:
                        self.__price = json[self.__id][self.__currency]
                        return True
                    else:
                        self.__price = None
                        return False
        except:
            self.__price = None
            return False

    def to_fiat(self, balance, digits=None):
        if self.__price is None:
            print(f'{balance}, {self.__price}')
            return None
        fiat = balance * self.__price
        return fiat if digits is None else round(fiat, digits)

    def to_fiat_string(self, balance, digits=2):
        return f'{self.to_fiat(balance, digits)} {self.currency}'
