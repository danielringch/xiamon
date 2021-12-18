import asyncio, yaml, os, aiohttp
from ssl import SSLContext
from .plugin import Plugin

__version__ = "0.1.0"

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chianode, self).__init__('chianode', outputs)
        self.print(f'Chianode plugin {__version__}')
        self.print(f'config file: {config}', True)
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)

        self.__path = config_data['path']

        self.__context = SSLContext()
        self.__context.load_cert_chain(config_data['cert'], keyfile=config_data['key'])

        scheduler.add_job('chianode' ,self.run, config_data['intervall'])

    async def run(self):
        peak = await self.__get_sync_state()
        await self.__get_connections(peak)

    async def __get_sync_state(self):
        json = await self.__post('get_blockchain_state')
        if not json["success"]:
            await self.send(f'Chia full node status request failed: no success', is_alert=True)
            return None
        is_synced = json['blockchain_state']['sync']['synced']
        peak = json['blockchain_state']['peak']['height']
        if is_synced:
            await self.send(f'Chia full node synced; peak {peak}.')
        elif json['blockchain_state']['sync']['sync_mode']:
            current_heigth = json['blockchain_state']['sync']['sync_progress_height']
            await self.send(f'Chia full node NOT synced; {current_heigth}/{peak}.', is_alert=True)
        else:
            await self.send(f'Chia full node offline.', is_alert=True)
        return peak

    async def __get_connections(self, peak):
        json = await self.__post('get_connections')
        if not json["success"]:
            await self.send(f'Chia full node connection status request failed: no success', is_alert=True)
            return
        nodes_count = 0
        synced_count = 0
        syncing_count = 0
        unkown_count = 0
        for node in json['connections']:
            if node['type'] != 1:
                continue
            node_peak = node['peak_height']
            if node_peak is None:
                unkown_count += 1
            elif peak is None:
                unkown_count += 1
            elif peak <= node_peak + 2:
                synced_count += 1
            else:
                syncing_count += 1
            nodes_count += 1
        message = '{0} nodes connected\nsynced={1}\nnot synced={2}\nunknown={3}'.format(nodes_count, synced_count, syncing_count, unkown_count)
        await self.send(message)


    async def __post(self, cmd):
        async with aiohttp.ClientSession() as session:
            async with session.post(f'https://127.0.0.1:8555/{cmd}', json={}, ssl_context=self.__context) as response:
                response.raise_for_status()
                return await response.json()
