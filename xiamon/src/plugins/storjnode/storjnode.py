from ...core import Plugin, Storjapi, ApiRequestFailedException, CsvExporter
from .storjdb import Storjdb
from .storjhost import Storjhost
from .storjstorage import Storjstorage
from .storjearning import Storjearning

class Storjnode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Storjnode, self).__init__(config, outputs)

        self.__hosts = [Storjhost(super(Storjnode, self), name, host) for name, host in self.config.data['hosts'].items()]

        self.__csv = CsvExporter(self.config.get(None, 'csv_export'))
        self.__db = Storjdb(self.config.data['database'])

        self.__storage = Storjstorage(self, scheduler, self.__db)
        self.__earning = Storjearning(self, scheduler, self.__db, self.__csv)

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        scheduler.add_job(f'{self.name}-accounting', self.accounting, self.config.get('0 0 2 0 0', 'accounting_interval'))

    async def check(self):
        async with Storjapi.create_session() as session:
            for host in self.__hosts:
                await host.check(session)

    async def summary(self):
        with self.message_aggregator():
            node_infos = {}
            payout_infos = {}
            async with Storjapi.create_session() as session:
                for host in self.__hosts:
                    try:
                        node_infos[host] = await host.get_node_info(session)
                        payout_infos[host] = await host.get_payout_info(session)
                    except ApiRequestFailedException:
                        self.msg.info('Summary is incomplete, data from {host.name} is missing.')
                        continue

            if len(node_infos) == 0 or len(payout_infos) == 0:
                self.msg.info('No summary created, no nodes are available.')
                return

            self.__storage.summary(node_infos, payout_infos)
            self.__earning.summary(payout_infos)

    async def accounting(self):
        with self.message_aggregator():
            payout_infos = {}
            async with Storjapi.create_session() as session:
                for host in self.__hosts:
                    try:
                        payout_infos[host] = await host.get_payout_info(session)
                    except ApiRequestFailedException:
                        self.msg.accounting('Accounting report is incomplete, data from {host.name} is missing.')
                        continue

            if len(payout_infos) == 0:
                self.msg.accounting('No accounting report created, no nodes are available.')
                return

            self.__earning.accounting(payout_infos)
