from collections import namedtuple, defaultdict
from enum import Enum
from ...core import Plugin, Conversions, Coinprice

class Siaautoprice:

    # name:
    # parameter:
    # target:
    # getter: 
    # unit: 
    # accurancy: 
    # converter: 
    # apiconverter: 
    UpdaterConfig = namedtuple("UpdaterConfig", "name parameter getter unit accurancy converter apiconverter")

    Category = Enum('Category', 'contract storage collateral upload download sector rpc')

    configs = {
        Category.contract : UpdaterConfig('contract', 'mincontractprice', lambda x: x.contractprice, 'SC', 4, lambda x, _: x, Conversions.siacoin_to_hasting),
        Category.storage : UpdaterConfig('storage', 'minstorageprice', lambda x: x.storageprice, 'SC / TB / month', 0, lambda x, y: x / y, Conversions.siacointerabytemonth_to_hastingsbyteblock),
        Category.collateral : UpdaterConfig('collateral', 'collateral', lambda x: x.collateral, 'SC / TB / month', 0, lambda x, y: x / y, Conversions.siacointerabytemonth_to_hastingsbyteblock),
        Category.upload : UpdaterConfig('upload', 'minuploadbandwidthprice', lambda x: x.uploadprice, 'SC / TB', 0, lambda x, y: x / y, Conversions.siacointerabyte_to_hastingbyte),
        Category.download : UpdaterConfig('download', 'mindownloadbandwidthprice', lambda x: x.downloadprice, 'SC / TB', 0, lambda x, y: x / y, Conversions.siacointerabyte_to_hastingbyte),
        Category.sector : UpdaterConfig('sector access', 'minsectoraccessprice', lambda x: x.sectorprice, 'SC', 10, lambda x, _: x, Conversions.siacoin_to_hasting),
        Category.rpc : UpdaterConfig('RPC', 'minbaserpcprice', lambda x: x.rpcprice, 'SC', 10, lambda x, _: x, Conversions.siacoin_to_hasting),
    }

    def __init__(self, plugin, api, coinprice, config):
        self.__plugin = plugin
        self.__api = api
        self.__coinprice = coinprice

        contract_price = config.data['autoprice']['contract']

        storage_price_fiat = config.data['autoprice']['storage']
        storage_price_sc, _ = config.get_value_or_default(None, 'autoprice', 'storage_max')

        upload_price_fiat = config.data['autoprice']['upload']
        upload_price_sc, _ = config.get_value_or_default(None, 'autoprice', 'upload_max')

        download_price_fiat = config.data['autoprice']['download']
        download_price_sc, _ = config.get_value_or_default(None, 'autoprice', 'download_max')

        sector_price = config.data['autoprice']['sector_access']

        rpc_price = config.data['autoprice']['base_rpc']

        self.__minimum_collateral_factor = config.data['autoprice']['minimum_collateral_factor']
        self.__maximum_collateral_factor = config.data['autoprice']['maximum_collateral_factor']
        self.__minimum_collateral_reserve = config.data['autoprice']['minimum_collateral_reserve']
        self.__target_collateral_reserve = config.data['autoprice']['target_collateral_reserve']

        self.__updaters = {
            self.Category.contract : self.Updater(self.configs[self.Category.contract], self.__coinprice, None, contract_price),
            self.Category.storage : self.Updater(self.configs[self.Category.storage], self.__coinprice, storage_price_fiat, storage_price_sc),
            self.Category.upload : self.Updater(self.configs[self.Category.upload], self.__coinprice, upload_price_fiat, upload_price_sc),
            self.Category.download : self.Updater(self.configs[self.Category.download], self.__coinprice, download_price_fiat, download_price_sc),
            self.Category.sector : self.Updater(self.configs[self.Category.sector], self.__coinprice, None, sector_price),
            self.Category.rpc : self.Updater(self.configs[self.Category.rpc], self.__coinprice, None, rpc_price)
        }

    def summary(self, storage, wallet, locked_collateral):
        collateral_reserve = self.__get_collateral_reserve(storage, wallet, locked_collateral)
        self.__plugin.send(Plugin.Channel.info, f'Collateral reserve: {collateral_reserve:.0f} %')

    async def update(self, host, storage, wallet, locked_collateral):
        messages = defaultdict(list)
        prices = {}

        messages[Plugin.Channel.debug].append(f'Coin price: {self.__coinprice.price} {self.__coinprice.currency} / SC')

        for updater in self.__updaters.values():
            self.__trigger_updater(host, updater, prices, messages)

        new_collateral = self.__update_collateral(
            self.__updaters[self.Category.storage].current_price,
            self.__get_collateral_reserve(storage, wallet, locked_collateral),
            messages)
        collateral_updater = self.Updater(self.configs[self.Category.collateral], self.__coinprice, None, new_collateral)
        self.__trigger_updater(host, collateral_updater, prices, messages)

        for channel, lines in messages.items():
            self.__plugin.send(channel, '\n'.join(lines))

        if len(prices) == 0:
            return

        async with self.__api.create_session() as session:
            try:
                await self.__api.post(session, 'host', prices)
            except Exception as e:
                print(e)
                self.__plugin.send(Plugin.Channel.alert, 'Price update failed.')
                return None

    def __get_collateral_reserve(self, storage, wallet, locked_collateral):
        used_factor = storage.used_space / storage.total_space
        locked_factor = locked_collateral / (locked_collateral + wallet.balance + wallet.pending)
        return round(100 * ((used_factor / locked_factor) - 1))

    def __update_collateral(self, storage_price, collateral_reserve, messages):
        collateral_reserve = max(self.__minimum_collateral_reserve, 
            min(self.__target_collateral_reserve, collateral_reserve))
        range_percent = (collateral_reserve - self.__minimum_collateral_reserve) / \
            (self.__target_collateral_reserve - self.__minimum_collateral_reserve)
        collateral_factor = round(((1 - range_percent) * self.__minimum_collateral_factor) + (range_percent * self.__maximum_collateral_factor), 2)
        messages[Plugin.Channel.debug].append(
            f'Collateral reserve: {collateral_reserve} % in range {self.__minimum_collateral_reserve} % .. {self.__target_collateral_reserve} %\n'
            f'New collateral factor: {collateral_factor} in range {self.__minimum_collateral_factor} .. {self.__maximum_collateral_factor}')
        return storage_price * collateral_factor

    def __trigger_updater(self, host, updater, prices, messages):
        new_price = updater.update(host, messages)
        if new_price is not None:
            key = new_price[0]
            value = f'{new_price[1]:d}'
            messages[Plugin.Channel.debug].append(f'Setting host parameter {key} to {value}')
            prices[key] = value

    class Updater:
        def __init__(self, config, coinprice, target_fiat, target_sc):
            self.__config = config
            self.__coinprice = coinprice
            self.__target_fiat = target_fiat
            self.__target_sc = target_sc

        def update(self, data, messages):
            current_price = self.__config.getter(data)

            new_prices = [
                round(self.__config.converter(self.__target_fiat, self.__coinprice.price), self.__config.accurancy) \
                    if self.__target_fiat is not None else None,
                self.__target_sc
            ]

            new_price = min((x for x in new_prices if x is not None), default=current_price)
            self.current_price = new_price

            if current_price != new_price:
                message = f'new {self.__config.name} price: {current_price} -> {new_price} {self.__config.unit}'
                messages[Plugin.Channel.report].append(message)
                messages[Plugin.Channel.info].append(message)
                return (self.__config.parameter, self.__config.apiconverter(new_price))
            else:
                messages[Plugin.Channel.report].append(f'{self.__config.name} price: {current_price} {self.__config.unit}')
                return None

