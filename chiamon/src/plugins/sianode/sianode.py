from ...core import Plugin, Alert, Siaapi, Siaconsensusdata, Config

class Sianode(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('sianode', 'name')
        super(Sianode, self).__init__(name, outputs)
        self.print(f'Plugin sianode; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        host, _ = config_data.get_value_or_default('127.0.0.1:9980','host')
        password = config_data.data['password']
        self.__api = Siaapi(host, password)

        self.__request_alerts = {
            'consensus' : Alert(super(Sianode, self), mute_interval)
        }
        self.__unsync_alert = Alert(super(Sianode, self), mute_interval)

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        await self.send(Plugin.Channel.debug, f'Checking state.')
        json = await self.__request('consensus')
        if json is not None:
            consensus = Siaconsensusdata(json)
            if not consensus.synced:
                await self.__unsync_alert.send(f'Sia node is not synced, height {consensus.height}.')
            else:
                await self.__unsync_alert.reset('Sia node is synced again.')
            await self.send(Plugin.Channel.debug, f'Synced: {consensus.synced} | Height: {consensus.height}')


    async def summary(self):
        json = await self.__request('consensus')
        if json is not None:
            consensus = Siaconsensusdata(json)
            await self.send(Plugin.Channel.info, f'Synced: {consensus.synced}\nHeight: {consensus.height}')
        else:
            await self.send(Plugin.Channel.info, f'No summary created, sia host unavailable.')
    
    async def __request(self, cmd):
        alert = self.__request_alerts[cmd]
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                await alert.reset(f'Request "{cmd}" is successful again.')
                return json
            except Exception as e:
                await alert.send(f'Request "{cmd}" failed.')
                return None