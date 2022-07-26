from datetime import timedelta
import statistics

from ...core import Plugin, Alert, Siaapi, Config, Conversions, Byteunit, Tablerenderer
from ...core import Siacontractsdata, Siaconsensusdata, Siahostdata, Siawalletdata, Siastoragedata
from .siaautoprice import Siaautoprice
from .siahealth import Siahealth
from .siastorage import Siastorage
from .siawallet import Siawallet

class Siahost(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('siahost', 'name')
        super(Siahost, self).__init__(name, outputs)
        self.print(f'Plugin siahost; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')
        self.__recent_intervall = Conversions.duration_to_siablocks(
            timedelta(hours=config_data.get_value_or_default(24, 'recent_intervall')[0]))

        host, _ = config_data.get_value_or_default('127.0.0.1:9980','host')
        password = config_data.data['password']
        self.__api = Siaapi(host, password)

        self.__request_alerts = {
            'consensus' : Alert(super(Siahost, self), mute_interval),
            'wallet' : Alert(super(Siahost, self), mute_interval),
            'host' : Alert(super(Siahost, self), mute_interval),
            'host/contracts' : Alert(super(Siahost, self), mute_interval),
            'host/storage' : Alert(super(Siahost, self), mute_interval)
        }

        self.__health = Siahealth(self, config_data)
        self.__storage = Siastorage(self)
        self.__wallet = Siawallet(self, config_data)
        self.__autoprice = None
        if 'autoprice' in  config_data.data:
            self.__autoprice = Siaautoprice(self, self.__api, config_data)
            scheduler.add_job(f'{name}-autoprice' ,self.price, config_data.get_value_or_default('0 0 * * *', 'price_interval')[0])

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-list', self.list, config_data.get_value_or_default('59 23 * * *', 'list_interval')[0])

    async def check(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None in (consensus, host, wallet):
            return
        
        await self.__health.check(consensus, host, wallet)

    async def summary(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None in (consensus, host, storage, contracts, wallet):
            await self.send(Plugin.Channel.info, 'No summary created, host is not available.')
            return

        await self.__health.summary(consensus, host, wallet)
        await self.__wallet.summary(host, storage, wallet)
        await self.__autoprice.summary(host, storage, wallet)
        await self.__storage.summary(storage)

        height = consensus.height

        ended_count = 0
        count = 0
        start_heights = []
        end_heights = []
        nearest_proof = None
        recent_started = 0
        soon_ending = 0

        for contract in contracts.contracts:
            if contract.proof_deadline > height and (nearest_proof is None or contract.proof_deadline < nearest_proof):
                nearest_proof = contract.proof_deadline
            if contract.end <= height:
                ended_count += 1
                continue
            count += 1
            blocks_since_start = height - contract.start
            blocks_unitl_end = contract.end - height
            start_heights.append(blocks_since_start)
            end_heights.append(blocks_unitl_end)
            if blocks_since_start <= self.__recent_intervall:
                recent_started += 1
            if blocks_unitl_end <= self.__recent_intervall:
                soon_ending += 1
            
            if count == 0:
                await self.send(Plugin.Channel.debug, f'No contracts.')
                return

        start_median = Conversions.siablocks_to_duration(round(statistics.median(start_heights)))
        end_median = Conversions.siablocks_to_duration(round(statistics.median(end_heights)))
        nearest_proof = Conversions.siablocks_to_duration(nearest_proof - height)

        await self.send(Plugin.Channel.info, (f'{count} contracts (+ {ended_count} ended)\n'
            f'Median contract: {start_median.days:.0f} d since start | {end_median.days:.0f} d until end\n'
            f'New contracts: {recent_started}\n'
            f'Ending contracts: {soon_ending}\n'
            f'Next proof deadline in {(nearest_proof.total_seconds() / 3600.0):.0f} h')) 

    async def list(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None not in (consensus, host, storage, contracts, wallet):
            await self.__wallet.dump(host, wallet)
            await self.__storage.report(storage)

            height = consensus.height
            id = 0
            renderer = Tablerenderer(['ID', 'Size', 'Started', 'Ending', 'Proof', 'Locked', 'Storage', 'Upload', 'Download'], 10)
            data = renderer.data
            for contract in sorted(contracts.contracts, key=lambda x: x.end):
                if contract.proof_deadline < height:
                    continue

                data['ID'].append(f'{id}')
                data['Size'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.byte_to_auto(contract.datasize)))
                data['Started'].append(f'{Conversions.siablocks_to_duration(height - contract.start).days} d')
                data['Ending'].append(f'{Conversions.siablocks_to_duration(contract.end - height).days} d')
                data['Proof'].append(f'{Conversions.siablocks_to_duration(contract.proof_deadline - height).days} d')
                data['Locked'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.locked_collateral)))
                data['Storage'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.storage_revenue)))
                data['Upload'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.upload_revenue)))
                data['Download'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.download_revenue)))
                id += 1
            await self.send(Plugin.Channel.debug, renderer.render())

    async def price(self):
        if self.__autoprice is None:
            return
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None in (host, storage, wallet):
            return
        await self.__autoprice.update(host, storage, wallet)

    async def __request(self, cmd, generator):
        alert = self.__request_alerts[cmd]
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                result = generator(json)
                await alert.reset(f'Request "{cmd}" is successful again.')
                return result
            except Exception as e:
                await alert.send(f'Request "{cmd}" failed.')
                return None
