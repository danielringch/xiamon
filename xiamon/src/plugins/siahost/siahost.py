from ...core import Plugin, Siaapi, Config, CsvExporter, Coinprice, ApiRequestFailedException
from ...core import Siacontractsdata, Siaconsensusdata, Siahostdata, Siawalletdata, Siastoragedata, Siatrafficdata
from .siaautoprice import Siaautoprice
from .siablocks import Siablocks
from .siadb import Siadb
from .siahealth import Siahealth
from .siacontracts import Siacontracts
from .siastorage import Siastorage
from .siawallet import Siawallet

class Siahost(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('siahost', 'name')
        super(Siahost, self).__init__(name, outputs)
        self.print(f'Plugin siahost; name: {name}')

        self.__scheduler = scheduler
        self.__check_job = f'{name}-check'
        self.__summary_job = f'{name}-summary'
        self.__list_job = f'{name}-list'
        self.__accounting_job = f'{name}-accounting'
        self.__autoprice_job = f'{name}-autoprice'
        self.__daychange_job = f'{name}-daychange'

        mute_interval = config_data.get(24, 'alert_mute_interval')

        host = config_data.get('127.0.0.1:9980','host')
        password = config_data.data['password']
        self.__api = Siaapi(host, password, super(Siahost, self))

        self.__db = Siadb(config_data.data['database'])
        self.__csv = CsvExporter(config_data.get(None, 'csv_export'))
        self.__blocks = Siablocks(super(Siahost, self), self.__api, self.__db)
        self.__coinprice = Coinprice('siacoin', config_data.data['currency'])

        self.__health = Siahealth(self, config_data)
        self.__storage = Siastorage(self, self.__scheduler, self.__db)
        self.__wallet = Siawallet(self, self.__db, self.__csv, self.__coinprice)
        self.__autoprice = None
        self.__reports = Siacontracts(self, self.__coinprice, self.__scheduler, self.__db, self.__blocks)
        if 'autoprice' in  config_data.data:
            self.__autoprice = Siaautoprice(self, self.__api, self.__coinprice, config_data)
            self.__scheduler.add_job(self.__autoprice_job ,self.price, config_data.get('0 0 * * *', 'price_interval'))

        self.__scheduler.add_job(self.__check_job ,self.check, config_data.get('0 * * * *', 'check_interval'))
        self.__scheduler.add_job(self.__summary_job, self.summary, config_data.get('0 0 * * *', 'summary_interval'))
        self.__scheduler.add_job(self.__list_job, self.list, config_data.get('59 23 * * *', 'list_interval'))
        self.__scheduler.add_job(self.__accounting_job, self.accounting, config_data.get('0 0 * * MON', 'accounting_interval'))
        self.__scheduler.add_job(self.__daychange_job, self.daychange, '59 23 * * *')

    async def check(self):
        with self.message_aggregator():
            try:
                consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
                host = await self.__request('host', lambda x: Siahostdata(x))
                wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
            except ApiRequestFailedException:
                self.msg.debug('Check failed: some host queries failed.')
                return
        
            await self.__blocks.update(consensus)
            self.__health.check(consensus, host, wallet)

    async def summary(self):
        with self.message_aggregator():
            try:
                consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
                host = await self.__request('host', lambda x: Siahostdata(x))
                storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
                traffic = await self.__request('host/bandwidth', lambda x: Siatrafficdata(x))
                contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
                wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
            except ApiRequestFailedException:
                self.msg.info('No summary created, host is not available.')
                return

            await self.__update_coinprice(Plugin.Channel.info, 'Summary is incomplete: coin price not available.')
            await self.__blocks.update(consensus)

            locked_collateral, risked_collateral = self.__get_collaterals(consensus, contracts)

            self.__health.update_proof_deadlines(contracts)
            self.__health.summary(consensus, host, wallet)
            await self.__wallet.summary(wallet, locked_collateral, risked_collateral)
            self.__autoprice.summary(storage, wallet, locked_collateral)
            self.__storage.summary(storage, traffic)
            await self.__reports.summary(consensus, contracts, self.__scheduler.get_last_execution(self.__summary_job))

    async def list(self):
        with self.message_aggregator():
            try:
                consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
                storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
                traffic = await self.__request('host/bandwidth', lambda x: Siatrafficdata(x))
                contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
                wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
            except ApiRequestFailedException:
                self.msg.error('Report failed: some host queries failed.')
                return

            await self.__update_coinprice(Plugin.Channel.error, 'Report incomplete: coin price not available.')
            await self.__blocks.update(consensus)

            self.__health.update_proof_deadlines(contracts)

            locked_collateral, risked_collateral = self.__get_collaterals(consensus, contracts)
            await self.__wallet.dump(wallet, locked_collateral, risked_collateral)
            self.__storage.report(storage, traffic)
            await self.__reports.contract_list(consensus, contracts)

    async def accounting(self):
        with self.message_aggregator():
            try:
                consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
                contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
            except ApiRequestFailedException:
                self.msg.error('Accounting failed: some host queries failed.')
                return

            await self.__update_coinprice(Plugin.Channel.error, 'Autoprice incomplete: coin price not available.')
            await self.__blocks.update(consensus)
            await self.__reports.accounting(consensus, contracts)

    async def price(self):
        with self.message_aggregator():
            if self.__autoprice is None:
                return
            try:
                host = await self.__request('host', lambda x: Siahostdata(x))
            except ApiRequestFailedException:
                self.msg.error('Autoprice failed: some host queries failed.')
                return

            if not await self.__update_coinprice(Plugin.Channel.error, 'Autoprice failed: coin price not available.'):
                return

            await self.__autoprice.update(host)

    async def daychange(self):
        await self.__update_coinprice(Plugin.Channel.error, 'Coin price update failed: coin price not available.')

    @staticmethod
    def __get_collaterals(consensus, contracts):
        height = consensus.height
        locked_collateral = 0
        risked_collateral = 0
        for contract in contracts.contracts:
            if contract.end <= height:
                continue
            locked_collateral += contract.locked_collateral
            risked_collateral += contract.risked_collateral

        return locked_collateral, risked_collateral


    async def __update_coinprice(self, error_channel, error_message):
        if not await self.__coinprice.update():
            self.msg[error_channel](error_message)
            return False
        else:
            self.__db.update_coinprice(self.__coinprice.price)
            return True

    async def __request(self, cmd, generator):
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                result = generator(json)
                return result
            except ApiRequestFailedException:
                raise
