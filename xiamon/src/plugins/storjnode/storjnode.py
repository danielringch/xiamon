from ...core import Plugin, Alert, Storjapi, Storjnodedata, Storjpayoutdata, Config, ApiRequestFailedException, CsvExporter
from .storjdb import Storjdb
from .storjstorage import Storjstorage
from .storjearning import Storjearning

class Storjnode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Storjnode, self).__init__(config, outputs)

        host = self.config.get('127.0.0.1:14002','host')
        self.__api = Storjapi(host, super(Storjnode, self))

        self.__csv = CsvExporter(self.config.get(None, 'csv_export'))
        self.__db = Storjdb(self.config.data['database'])

        self.__storage = Storjstorage(self, scheduler, self.__db)
        self.__earning = Storjearning(self, scheduler, self.__db, self.__csv)

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        scheduler.add_job(f'{self.name}-report', self.report, self.config.get('0 0 2 0 0', 'report_interval'))

    async def check(self):
        try:
            data = await self.__request('sno/', lambda x: Storjnodedata(x))
        except ApiRequestFailedException:
            return
        
        if not data.uptodate:
            self.alert('version', 'Node version is outdated.')
        else:
            self.reset_alert('version', 'Node version is up to date.')

        if not data.quic:
            self.alert('quic', 'QUIC is disabled.')
        else:
            self.reset_alert('quic', 'QUIC is enabled again.')

        if data.satellites == 0:
            self.alert('sat', 'Node is offline.')
        else:
            self.reset_alert('sat', f'Node is online again, {data.satellites} satellites.')

        if data.disqualified > 0:
            self.alert('disq', f'Node is disqualified for {data.disqualified} satellites.')
        else:
            self.reset_alert('disq', 'Node is no longer disqualified for any satellite.')

        if data.suspended > 0:
            self.alert('susp', f'Node is suspended for {data.disqualified} satellites.')
        else:
            self.reset_alert('susp', 'Node is no longer suspended for any satellite.')

        if data.overused_space > 0:
            self.alert('overu', f'Node overuses {data.overused_space} bytes storage.')
        else:
            self.reset_alert('overu', 'Node does no longer overuse storage.')

    async def summary(self):
        with self.message_aggregator():
            try:
                node = await self.__request('sno/', lambda x: Storjnodedata(x))
                payout = await self.__request('sno/estimated-payout', lambda x: Storjpayoutdata(x))
            except ApiRequestFailedException:
                self.msg.info('No summary created, node is not available.')
                return

        self.__storage.summary(node, payout)
        self.__earning.summary(payout)

    async def report(self):
        with self.message_aggregator():
            try:
                payout = await self.__request('sno/estimated-payout', lambda x: Storjpayoutdata(x))
            except ApiRequestFailedException:
                self.msg.info('No report created, node is not available.')
                return

        self.__earning.report(payout)

    async def __request(self, cmd, generator):
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                result = generator(json)
                return result
            except ApiRequestFailedException:
                raise