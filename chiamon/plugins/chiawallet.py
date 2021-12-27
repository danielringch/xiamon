import yaml, aiohttp
from ssl import SSLContext
from .plugin import Plugin
from .utils.alert import Alert

__version__ = "0.1.1"

class Chiawallet(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chiawallet, self).__init__('chiawallet', outputs)
        self.print(f'Chiawallet plugin {__version__}')
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)

        self.__context = SSLContext()
        self.__context.load_cert_chain(config_data['cert'], keyfile=config_data['key'])

        mute_intervall = config_data['alert_mute_interval']
        self.__rpc_failed_alert = Alert(super(Chiawallet, self), mute_intervall)
        self.__wallet_unsynced_alert = Alert(super(Chiawallet, self), mute_intervall)

        self.__wallet_id = config_data['wallet_id']
        self.__balance = None

        scheduler.add_job('chiawallet-check' ,self.check, config_data['check_intervall'])
        scheduler.add_job('chiawallet-summary', self.summary, config_data['summary_intervall'])

    async def check(self):
        raw_balance = await self.__get_balance()
        if not raw_balance:
            return
        diff = raw_balance - self.__balance if self.__balance else 0
        if diff != 0:
            self.__balance = raw_balance
            await self.send(f'Balance changed: {self.__mojo_to_xch(diff)} XCH\nNew balance: {self.__mojo_to_xch(raw_balance)} XCH', True)

    async def summary(self):
        raw_balance = await self.__get_balance()
        if not raw_balance:
            return
        await self.send(f'Wallet balance: {self.__mojo_to_xch(raw_balance)} XCH')

    async def __get_balance(self):
        if not await self.__get_synced():
            return None
        json = await self.__post('get_wallet_balance', {'wallet_id': self.__wallet_id})
        if not json["success"]:
            await self.__rpc_failed_alert.send('Chia wallet balance request failed: no success')
            return None
        return json['wallet_balance']['confirmed_wallet_balance']

    async def __get_synced(self):
        json = await self.__post('get_sync_status')
        if not json["success"]:
            await self.__rpc_failed_alert.send('Chia wallet sync status request failed: no success')
            return False
        synced = json['synced']
        if not synced:
            syncing = json['syncing']
            not_synced_message = 'Chia wallet is syncing.' if syncing else 'Chia wallet is not synced.'
            await self.__wallet_unsynced_alert.send(not_synced_message)
        return synced

    async def __post(self, cmd, data={}):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f'https://127.0.0.1:9256/{cmd}', json=data, ssl_context=self.__context) as response:
                    response.raise_for_status()
                    return await response.json()
        except:
            return {"success": False}

    def __mojo_to_xch(self, mojo):
        return mojo / 1000000000000.0

