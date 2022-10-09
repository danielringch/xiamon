import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config
from .nodeconnections import Nodeconnections
from .nodesyncstate import NodeSyncState

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chianode', 'name')
        super(Chianode, self).__init__(name, outputs)
        self.print(f'Plugin chianode; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:8555','host')
        self.__rpc = Chiarpc(host, config_data.data['cert'], config_data.data['key'], super(Chianode, self))

        self.__node_unsynced_alert = Alert(super(Chianode, self), mute_interval)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

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
                message = f'Full node synced; height {state.height}.'
            elif state.height is not None:
                message = f'Full node syncing: {state.height}/{state.peak}.'
            else:
                message = f'Full node not synced.'
            self.send(Plugin.Channel.info, message)
            if connections.available:
                message = (
                    f'Connected full nodes: {connections.synced + connections.syncing + connections.unknown}\n'
                    f'Sync states (synced | not synced | unknown): {connections.synced} | {connections.syncing} | {connections.unknown}\n'
                    f'Wallets: {connections.wallets}\n'
                    f'Other node types: {connections.other}'
                )
                self.send(Plugin.Channel.info, message)
        else:
            self.send(Plugin.Channel.info, f'No summary created, since node is not available.')
