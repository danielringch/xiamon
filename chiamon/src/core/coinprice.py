import aiohttp, datetime

class Coinprice:
    def __init__(self, id, currency):
        self.__id = id
        self.__currency = currency
        self.__price = None
        self.__last_update = datetime.datetime.min

    @property
    def currency(self):
        return self.__currency.upper()

    @property
    def price(self):
        return self.__price

    async def update(self):
        now = datetime.datetime.now()
        if (now - self.__last_update) < datetime.timedelta(minutes=1):
            return True
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.coingecko.com/api/v3/simple/price?ids={self.__id}&vs_currencies={self.__currency}') as response:
                    json = await response.json()
                    status = response.status
                    if status >= 200 and status <= 299:
                        self.__price = json[self.__id][self.__currency]
                        self.__last_update = now
                        return True
                    else:
                        self.__price = None
                        return False
        except:
            self.__price = None
            return False

    def to_fiat(self, *balances):
        try:
            result = []
            for balance in balances:
                result.append(round(balance * self.__price, 2))
            return result
        except:
            return [None] * len(balances)

    def to_fiat_string(self, *balances):
        try:
            fiats = self.to_fiat(*balances)
            result = []
            for fiat in fiats:
                result.append(f'{fiat:.2f} {self.__currency.upper()}')
            return result
        except:
            return [''] * len(balances)
