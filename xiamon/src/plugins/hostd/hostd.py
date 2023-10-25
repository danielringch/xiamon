from ...core import Plugin, Hostdapi, CsvExporter, Coinprice, ApiRequestFailedException
from ...core import Hostdconsensusdata, Hostdwalletdata, Hostdmetricsdata
from .hostddb import Hostddb
from .hostdhealth import Hostdhealth
from .hostdstorage import Hostdstorage
from .hostdwallet import Hostdwallet

class Hostd(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Hostd, self).__init__(config, outputs)

        self.__scheduler = scheduler
        self.__check_job = f'{self.name}-check'
        self.__summary_job = f'{self.name}-summary'
        self.__list_job = f'{self.name}-list'
        self.__accounting_job = f'{self.name}-accounting'
        self.__autoprice_job = f'{self.name}-autoprice'
        self.__daychange_job = f'{self.name}-daychange'
        self.__startup_job = f'{self.name}-startup'

        host = self.config.get('127.0.0.1:9980','host')
        password = self.config.data['password']
        self.__api = Hostdapi(host, password, self)

        self.__db = Hostddb(self.config.data['database'])
        self.__csv = CsvExporter(self.config.get(None, 'csv_export'))
        self.__coinprice = Coinprice('siacoin', self.config.data['currency'])

        self.__health = Hostdhealth(self, self.config)
        self.__storage = Hostdstorage(self)
        self.__wallet = Hostdwallet(self, self.__db, self.__csv, self.__coinprice)

        self.__scheduler.add_job(self.__check_job ,self.check, self.config.get('0 * * * *', 'check_interval'))
        self.__scheduler.add_job(self.__summary_job, self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        self.__scheduler.add_job(self.__list_job, self.list, self.config.get('59 23 * * *', 'list_interval'))
        self.__scheduler.add_job(self.__accounting_job, self.accounting, self.config.get('0 0 * * MON', 'accounting_interval'))
        self.__scheduler.add_job(self.__daychange_job, self.daychange, '59 23 * * *')
        self.__scheduler.add_startup_job(self.__startup_job, self.startup)

    async def startup(self):
        pass

    async def check(self):
        with self.message_aggregator():
            try:
                consensus = await self.__request('state/consensus', lambda x: Hostdconsensusdata(x))
                wallet = await self.__request('wallet', lambda x: Hostdwalletdata(x))
            except ApiRequestFailedException:
                self.msg.debug('Check failed: some host queries failed.')
                return
        
            self.__health.check(consensus, wallet)

    async def summary(self):
        with self.message_aggregator():
            last_execution = self.__scheduler.get_last_execution(self.__summary_job)
            try:
                consensus = await self.__request('state/consensus', lambda x: Hostdconsensusdata(x))
                wallet = await self.__request('wallet', lambda x: Hostdwalletdata(x))
                metrics = await self.__request('metrics', lambda x: Hostdmetricsdata(x))
                last_metrics = await self.__request('metrics', lambda x: Hostdmetricsdata(x), payload={'timestamp': self.__get_iso_date_time(last_execution)})
            except ApiRequestFailedException:
                self.msg.info('No summary created, host is not available.')
                return

            await self.__update_coinprice(Plugin.Channel.info, 'Summary is incomplete: coin price not available.')

            self.__health.summary(consensus)
            await self.__wallet.summary(wallet, metrics)
            self.__storage.summary(metrics, last_metrics)

    async def list(self):
        with self.message_aggregator():
            try:
                wallet = await self.__request('wallet', lambda x: Hostdwalletdata(x))
                metrics = await self.__request('metrics', lambda x: Hostdmetricsdata(x))
            except ApiRequestFailedException:
                self.msg.error('Report failed: some host queries failed.')
                return

            await self.__update_coinprice(Plugin.Channel.error, 'Report incomplete: coin price not available.')

            await self.__wallet.dump(wallet, metrics)

    async def accounting(self):
        with self.message_aggregator():
            pass

    async def price(self):
        with self.message_aggregator():
            pass

    async def daychange(self):
        pass

    async def __update_coinprice(self, error_channel, error_message):
        if not await self.__coinprice.update():
            self.msg[error_channel](error_message)
            return False
        else:
            self.__db.update_coinprice(self.__coinprice.price)
            return True
        
    def __get_iso_date_time(self, timestamp):
        tz_dt = timestamp.astimezone()
        return tz_dt.isoformat()

    async def __request(self, cmd, generator, payload={}):
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd, payload)
                result = generator(json)
                return result
            except ApiRequestFailedException:
                raise
