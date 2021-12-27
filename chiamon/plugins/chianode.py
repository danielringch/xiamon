import yaml, aiohttp
from ssl import SSLContext
from .plugin import Plugin
from .utils.alert import Alert

__version__ = "0.2.1"

class Chianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chianode, self).__init__('chianode', outputs)
        self.print(f'Chianode plugin {__version__}')
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)

        self.__context = SSLContext()
        self.__context.load_cert_chain(config_data['cert'], keyfile=config_data['key'])

        mute_intervall = config_data['alert_mute_interval']
        self.__rpc_failed_alert = Alert(super(Chianode, self), mute_intervall)
        self.__node_unsynced_alert = Alert(super(Chianode, self), mute_intervall)

        scheduler.add_job('chianode-check' ,self.check, config_data['check_intervall'])
        scheduler.add_job('chianode-summary', self.summary, config_data['summary_intervall'])

    async def check(self):
        self.print('Checking chia sync state.')
        _ = await self.__get_sync_state(True)

    async def summary(self):
        peak = await self.__get_sync_state()
        await self.__get_connections(peak)

    async def __get_sync_state(self, muted=False):
        json = await self.__post('get_blockchain_state')
        if not json["success"]:
            await self.__rpc_failed_alert.send('Chia full node status request failed: no success')
            return None 
        synced = json['blockchain_state']['sync']['synced']
        peak = json['blockchain_state']['peak']['height']
        if not synced:
            message = 'Chia full node offline.'
            if json['blockchain_state']['sync']['sync_mode']:
                current_heigth = json['blockchain_state']['sync']['sync_progress_height']
                message = f'Chia full node NOT synced; {current_heigth}/{peak}.'
            await self.__node_unsynced_alert.send(message)
            return peak
        if not muted:
            await self.send(f'Chia full node synced; peak {peak}.')
        return peak

    async def __get_connections(self, peak):
        json = await self.__post('get_connections')
        if not json["success"]:
            await self.__rpc_failed_alert.send(f'Chia full node connection status request failed: no success')
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'https://127.0.0.1:8555/{cmd}', json={}, ssl_context=self.__context) as response:
                    response.raise_for_status()
                    return await response.json()
        except:
            return {"success": False}

