from ...core import Plugin, Alert, Storjapi, Storjnodedata, Storjpayoutdata, Config, ApiRequestFailedException
from .storjdb import Storjdb
from .storjstorage import Storjstorage
from .storjearning import Storjearning

class Storjnode(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('storjnode', 'name')
        super(Storjnode, self).__init__(name, outputs)
        self.print(f'Plugin storjnode; name: {name}')

        mute_interval = config_data.get(24, 'alert_mute_interval')

        host = config_data.get('127.0.0.1:14002','host')
        self.__api = Storjapi(host, super(Storjnode, self))

        self.__db = Storjdb(config_data.data['database'])

        self.__storage = Storjstorage(self, scheduler, self.__db)
        self.__earning = Storjearning(self, scheduler, self.__db)

        self.__outdated_alert = Alert(super(Storjnode, self), mute_interval)
        self.__quic_alert = Alert(super(Storjnode, self), mute_interval)
        self.__offline_alert = Alert(super(Storjnode, self), mute_interval)
        self.__offline_alert = Alert(super(Storjnode, self), mute_interval)
        self.__disqualified_alert = Alert(super(Storjnode, self), mute_interval)
        self.__suspended_alert = Alert(super(Storjnode, self), mute_interval)
        self.__overused_alert = Alert(super(Storjnode, self), mute_interval)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get('0 0 * * *', 'summary_interval'))
        scheduler.add_job(f'{name}-report', self.report, config_data.get('0 0 2 0 0', 'report_interval'))

    async def check(self):
        try:
            data = await self.__request('sno/', lambda x: Storjnodedata(x))
        except ApiRequestFailedException:
            return
        
        if not data.uptodate:
            self.__outdated_alert.send('Node version is outdated.')

        if not data.quic:
            self.__quic_alert.send('QUIC is disabled.')
        else:
            self.__quic_alert.reset('QUIC is enabled again.')

        if data.satellites == 0:
            self.__offline_alert.send('Node is offline.')
        else:
            self.__offline_alert.reset(f'Node is online again, {data.satellites} satellites.')

        if data.disqualified > 0:
            self.__disqualified_alert.send(f'Node is disqualified for {data.disqualified} satellites.')
        else:
            self.__disqualified_alert.reset('Node is no longer disqualified for any satellite.')

        if data.suspended > 0:
            self.__suspended_alert.send(f'Node is suspended for {data.disqualified} satellites.')
        else:
            self.__suspended_alert.reset('Node is no longer suspended for any satellite.')

        if data.overused_space > 0:
            self.__overused_alert.send(f'Node overuses {data.overused_space} bytes storage.')
        else:
            self.__overused_alert.reset('Node does no longer overuse storage.')

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