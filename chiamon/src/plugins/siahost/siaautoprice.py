from ...core import Plugin, Conversions, Coinprice

class Siaautoprice:
    def __init__(self, plugin, api, config):
        self.__plugin = plugin
        self.__api = api
        self.__coinprice = Coinprice('siacoin', config.data['autoprice']['currency'])

        self.__storage_price = config.data['autoprice']['storage']
        self.__minimum_collateral_factor = config.data['autoprice']['minimum_collateral_factor']
        self.__maximum_collateral_factor = config.data['autoprice']['maximum_collateral_factor']
        self.__minimum_collateral_reserve = config.data['autoprice']['minimum_collateral_reserve']
        self.__target_collateral_reserve = config.data['autoprice']['target_collateral_reserve']

        self.__updaters = []
        self.__updaters.append(Siaautoprice.ContractUpdater(self.__coinprice, config.data['autoprice']['contract']))
        self.__updaters.append(Siaautoprice.StorageUpdater(self.__coinprice, self.__storage_price))
        self.__collateral_updater = Siaautoprice.CollateralUpdater(self.__coinprice, 0)
        self.__updaters.append(self.__collateral_updater)
        self.__updaters.append(Siaautoprice.UploadUpdater(self.__coinprice, config.data['autoprice']['upload']))
        self.__updaters.append(Siaautoprice.DownloadUpdater(self.__coinprice, config.data['autoprice']['download']))
        self.__updaters.append(Siaautoprice.SectorUpdater(self.__coinprice, config.data['autoprice']['sector_access']))
        self.__updaters.append(Siaautoprice.RpcUpdater(self.__coinprice, config.data['autoprice']['base_rpc']))

    async def summary(self, host, storage, wallet):
        collateral_reserve = self.__get_collateral_reserve(host, storage, wallet)
        await self.__plugin.send(Plugin.Channel.info, f'Collateral reserve: {collateral_reserve:.0f} %')

    async def update(self, host, storage, wallet):
        debug_message = []
        info_message = []
        report_message = []
        prices = {}

        if not await self.__coinprice.update():
            await self.__plugin.send(Plugin.Channel.alert, 'Price update failed, no coin price available.')
            return

        debug_message.append(f'Coin price: {self.__coinprice.price} {self.__coinprice.currency.upper()} / SC')

        collateral_reserve = max(self.__minimum_collateral_reserve, 
            min(self.__target_collateral_reserve, 
                self.__get_collateral_reserve(host, storage, wallet)))
        range_percent = (collateral_reserve - self.__minimum_collateral_reserve) / \
            (self.__target_collateral_reserve - self.__minimum_collateral_reserve)
        collateral_factor = round(((1 - range_percent) * self.__minimum_collateral_factor) + (range_percent * self.__maximum_collateral_factor), 2)
        await self.__plugin.send(Plugin.Channel.debug, (
            f'Collateral reserve: {collateral_reserve} % in range {self.__minimum_collateral_reserve} % .. {self.__target_collateral_reserve} %\n'
            f'New collateral factor: {collateral_factor} in range {self.__minimum_collateral_factor} .. {self.__maximum_collateral_factor}'))
        self.__collateral_updater.target = self.__storage_price * collateral_factor

        for updater in self.__updaters:
            new_price = updater.update(host)
            report_message.append(updater.report_message)
            if(updater.info_message is not None):
                info_message.append(updater.info_message)
            if new_price is not None:
                key = new_price[0]
                value = f'{new_price[1]:d}'
                debug_message.append(f'Setting host parameter {key} to {value}')
                prices[key] = value

        await self.__plugin.send(Plugin.Channel.report, '\n'.join(report_message))
        if len(info_message) > 0:
            await self.__plugin.send(Plugin.Channel.info, '\n'.join(info_message))
        if len(debug_message) > 0:
            await self.__plugin.send(Plugin.Channel.debug, '\n'.join(debug_message))
        if len(prices) == 0:
            return

        async with self.__api.create_session() as session:
            try:
                await self.__api.post(session, 'host', prices)
            except Exception as e:
                print(e)
                await self.__plugin.send(Plugin.Channel.alert, 'Price update failed.')
                return None

    def __get_collateral_reserve(self, host, storage, wallet):
        used_factor = storage.used_space / storage.total_space
        locked_factor = host.lockedcollateral / (host.lockedcollateral + wallet.balance + wallet.pending)
        return round(100 * ((used_factor / locked_factor) - 1))

    class Updater:
        def __init__(self, name, parameter, target, getter, coinprice, unit='SC', accurancy=0, converter=lambda x, _: x, api_converter=Conversions.siacoin_to_hasting):
            self.__name = name
            self.__parameter = parameter
            self.target = target
            self.__unit = unit
            self.__accurancy = accurancy
            self.__converter = converter
            self.__api_converter = api_converter
            self.__getter = getter
            self.__coinprice = coinprice
            self.report_message = None
            self.info_message = None

        def update(self, data):
            current = self.__getter(data)
            target = round(self.__converter(self.target, self.__coinprice.price), self.__accurancy)
            if current != target:
                self.report_message = f'new {self.__name} price: {current} -> {target} {self.__unit}'
                self.info_message = self.report_message
                return (self.__parameter, self.__api_converter(target))
            else:
                self.report_message = f'{self.__name} price: {current} {self.__unit}'
                self.info_message = None
                return None


    class ContractUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='contract',
                parameter='mincontractprice',
                target=target,
                getter=lambda x: x.contractprice,
                coinprice=coinprice,
                accurancy=4)

    class StorageUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='storage',
                parameter='minstorageprice',
                target=target,
                getter=lambda x: x.storageprice,
                coinprice=coinprice,
                unit='SC / TB / month',
                converter=lambda x,y: x / y,
                api_converter=Conversions.siacointerabytemonth_to_hastingsbyteblock)

    class CollateralUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='collateral',
                parameter='collateral',
                target=target,
                getter=lambda x: x.collateral,
                coinprice=coinprice,
                unit='SC / TB / month',
                converter=lambda x,y: x / y,
                api_converter=Conversions.siacointerabytemonth_to_hastingsbyteblock)

    class UploadUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='upload',
                parameter='minuploadbandwidthprice',
                target=target,
                getter=lambda x: x.uploadprice,
                coinprice=coinprice,
                unit='SC / TB',
                converter=lambda x,y: x / y,
                api_converter=Conversions.siacointerabyte_to_hastingbyte)

    class DownloadUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='download',
                parameter='mindownloadbandwidthprice',
                target=target,
                getter=lambda x: x.downloadprice,
                coinprice=coinprice,
                unit='SC / TB',
                converter=lambda x,y: x / y,
                api_converter=Conversions.siacointerabyte_to_hastingbyte)

    class SectorUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='sector access',
                parameter='minsectoraccessprice',
                target=target,
                getter=lambda x: x.sectorprice,
                coinprice=coinprice,
                accurancy=10)

    class RpcUpdater(Updater):
        def __init__(self, coinprice, target):
            Siaautoprice.Updater.__init__(self,
                name='RPC',
                parameter='minbaserpcprice',
                target=target,
                getter=lambda x: x.rpcprice,
                coinprice=coinprice,
                accurancy=10)

