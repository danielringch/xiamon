import aiohttp
from ..core import Plugin, Alert, Chiarpc, Config

__version__ = "0.3.0"

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chianode, self).__init__('chianode', outputs)
        self.print(f'Chianode plugin {__version__}')

        config_data = Config(config)

        self.__host, _ = config_data.get_value_or_default('127.0.0.1:8555','host')
        self.__mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        self.__rpc = Chiarpc(self.__host, config_data.data['cert'], config_data.data['key'],
            super(Chianode, self), self.__mute_interval)

        self.__node_unsynced_alert = Alert(super(Chianode, self), self.__mute_interval)

        scheduler.add_job('chianode-check' ,self.check, config_data.get_value_or_default('0 0 * * *', 'check_interval')[0])
        scheduler.add_job('chianode-summary', self.summary, config_data.get_value_or_default('0 * * * *', 'summary_interval')[0])

    async def check(self):
        await self.send(Plugin.Channel.debug, f'Checking sync state of {self.__host}.')
        async with aiohttp.ClientSession() as session:
            _, _, _ = await self.__get_sync_state(session)

    async def summary(self):
        await self.send(Plugin.Channel.debug, f'Creating summary for {self.__host}.')
        async with aiohttp.ClientSession() as session:
            synced, height, peak = await self.__get_sync_state(session)
            synced_nodes, syncing_nodes, unknown_nodes, other_nodes = await self.__get_connections(session, peak)
        if (synced is not None) and (synced_nodes is not None):
            if synced:
                message = f'Full node synced; height {height}.'
            elif height is not None:
                message = f'Full node syncing: {height}/{peak}.'
            else:
                message = f'Full node not synced.'
            await self.send(Plugin.Channel.info, message)
            message = (
                f'Connected full nodes: {synced_nodes + syncing_nodes + unknown_nodes}\n'
                f'Sync states (synced | not synced | unknown): {synced_nodes} | {syncing_nodes} | {unknown_nodes}\n'
                f'Other node types: {other_nodes}'
            )
            await self.send(Plugin.Channel.info, message)
        else:
            await self.send(Plugin.Channel.info, f'No summary created, since node is not available.')

    async def __get_sync_state(self, session):
        json = await self.__rpc.post(session, 'get_blockchain_state')
        if json is None:
            return None, None, None
        json = json['blockchain_state']
        synced = json['sync']['synced']
        if not synced:
            peak = json['sync']['sync_tip_height']
            if json['sync']['sync_mode']:
                height = json['sync']['sync_progress_height']
                await self.__node_unsynced_alert.send(f'Full node NOT synced; {height}/{peak}.', 'syncing')
            else:
                height = None
                await self.__node_unsynced_alert.send('Full node stalled.', 'stalled')
        else:
            peak = json['peak']['height']
            height = peak
            await self.__node_unsynced_alert.reset('Full node synced again.')
        return synced, height, peak

    async def __get_connections(self, session, peak):
        json = await self.__rpc.post(session, 'get_connections')
        if json is None:
            return None, None, None, None
        synced = 0
        syncing = 0
        unknown = 0
        other = 0
        for node in json['connections']:
            if node['type'] != 1:
                other += 1
                continue
            node_peak = node['peak_height']
            if node_peak is None:
                unknown += 1
            elif peak is None:
                unknown += 1
            elif peak <= node_peak + 2:
                synced += 1
            else:
                syncing += 1
        return synced, syncing, unknown, other
