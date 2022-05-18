
class Nodeconnections:
    @classmethod
    async def create(cls, rpc, session, peak):
        result = Nodeconnections()
        json = await rpc.post(session, 'get_connections')
        if json is None:
            return result
        result.available = True
        for node in json['connections']:
            if node['type'] == 6:
                result.wallets += 1
            elif node['type'] != 1:
                result.other += 1
                continue
            node_peak = node['peak_height']
            if node_peak is None:
                result.unknown += 1
            elif peak is None:
                result.unknown += 1
            elif peak <= node_peak + 2:
                result.synced += 1
            else:
                result.syncing += 1
        return result

    def __init__(self):
        self.available = False
        self.synced = 0
        self.syncing = 0
        self.unknown = 0
        self.wallets = 0
        self.other = 0
