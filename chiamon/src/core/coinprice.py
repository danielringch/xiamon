import aiohttp

class Coinprice:
    def __init__(self, id, currency):
        self.__id = id
        self.__currency = currency

    async def get(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.coingecko.com/api/v3/simple/price?ids={self.__id}&vs_currencies={self.__currency}') as response:
                    json = await response.json()
                    status = response.status
                    if status >= 200 and status <= 299:
                        return json[self.__id][self.__currency]
                    else:
                        return 0.0
        except:
            return 0.0

    async def to_fiat(self, *balances):
        price = await self.get()
        result = []
        for balance in balances:
            result.append(balance * price)
        return result

    async def to_fiat_string(self, *balances):
        fiats = await self.to_fiat(*balances)
        result = []
        for fiat in fiats:
            result.append(f'{fiat:.2f} {self.__currency.upper()}')
        return result
