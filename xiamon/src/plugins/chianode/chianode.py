import aiohttp
from ...core import Plugin, Chiarpc
from .nodeconnections import Nodeconnections
from .nodesyncstate import NodeSyncState

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chianode, self).__init__(config, outputs)
        
        host = self.config.get('127.0.0.1:8555', 'host')
        self.__rpc = Chiarpc(host, self.config.data['cert'], self.config.data['key'], super(Chianode, self))

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('0 * * * *', 'check_interval'))
        scheduler.add_job(f'{self.name}-summary', self.summary, self.config.get('0 0 * * *', 'summary_interval'))

    async def check(self):
        async with aiohttp.ClientSession() as session:
            state = await NodeSyncState.create(self.__rpc, session)
            if not state.available or (not state.synced and state.height is None):
                self.alert('unsynced', 'Full node stalled.', 'stalled')
            elif state.synced:
                self.reset_alert('unsynced', 'Full node synced again.')
            else:
                self.alert('unsynced', f'Full node NOT synced; {state.height}/{state.peak}.', 'syncing')

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
