from ...core import ApiRequestFailedException

class NodeSyncState:
    @classmethod
    async def create(cls, rpc, session):
        result = NodeSyncState()
        try:
            json = await rpc.post(session, 'get_blockchain_state')
        except ApiRequestFailedException:
            return result
        result.available = True
        json = json['blockchain_state']
        synced = json['sync']['synced']
        height = None
        peak = 0
        if not synced:
            peak = json['sync']['sync_tip_height']
            if json['sync']['sync_mode']:
                height = json['sync']['sync_progress_height']
        else:
            peak = json['peak']['height']
            height = peak

        result.synced = synced
        result.height = height
        result.peak = peak

        return result

    def __init__(self):
        self.available = False
        self.synced = False
        self.height = None
        self.peak = 0
