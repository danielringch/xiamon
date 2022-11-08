import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config
from .nodeconnections import Nodeconnections
from .nodesyncstate import NodeSyncState

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('chianode', 'name')
        super(Chianode, self).__init__(name, outputs)
        self.print(f'Plugin chianode; name: {name}')

        mute_interval = config_data.get(24, 'alert_mute_interval')

        host = config_data.get('127.0.0.1:8555', 'host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'], super(Chianode, self))

        self.__node_unsynced_alert = Alert(super(Chianode, self), mute_interval)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get('0 0 * * *', 'summary_interval'))

    async def check(self):
        async with aiohttp.ClientSession() as session:
            state = await NodeSyncState.create(self.__rpc, session)
            if not state.available or (not state.synced and state.height is None):
                self.__node_unsynced_alert.send('Full node stalled.', 'stalled')
            elif state.synced:
                self.__node_unsynced_alert.reset('Full node synced again.')
            else:
                self.__node_unsynced_alert.send(f'Full node NOT synced; {state.height}/{state.peak}.', 'syncing')

    async def summary(self):
        async with aiohttp.ClientSession() as session:
            state = await NodeSyncState.create(self.__rpc, session)
            connections = await Nodeconnections.create(self.__rpc, session, state.peak)
        if state.available:
            if state.synced:
                self.msg.info(f'Full node synced; height {state.height}.')
            elif state.height is not None:
                self.msg.info(f'Full node syncing: {state.height}/{state.peak}.')
            else:
                self.msg.info(f'Full node not synced.')
            if connections.available:
                self.msg.info(
                    f'Connected full nodes: {connections.synced + connections.syncing + connections.unknown}',
                    f'Sync states (synced | not synced | unknown): {connections.synced} | {connections.syncing} | {connections.unknown}',
                    f'Wallets: {connections.wallets}',
                    f'Other node types: {connections.other}'
                )
        else:
            self.msg.info(f'No summary created, since node is not available.')
