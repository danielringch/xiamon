from datetime import datetime, timedelta
import statistics

from ...core import Plugin, Alert, Siaapi, Config, Conversions, Byteunit, Tablerenderer, Coinprice
from ...core import Siacontractsdata, Siaconsensusdata, Siahostdata, Siawalletdata, Siastoragedata
from .siaautoprice import Siaautoprice
from .siablocks import Siablocks
from .siahealth import Siahealth
from .siareports import Siareports
from .siastorage import Siastorage
from .siawallet import Siawallet

class Siahost(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('siahost', 'name')
        super(Siahost, self).__init__(name, outputs)
        self.print(f'Plugin siahost; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')
        self.__recent_intervall = timedelta(hours=config_data.get_value_or_default(24, 'recent_intervall')[0])

        host, _ = config_data.get_value_or_default('127.0.0.1:9980','host')
        password = config_data.data['password']
        self.__api = Siaapi(host, password)

        self.__coinprice = Coinprice('siacoin', config_data.data['currency'])

        self.__request_alerts = {
            'consensus' : Alert(super(Siahost, self), mute_interval),
            'wallet' : Alert(super(Siahost, self), mute_interval),
            'host' : Alert(super(Siahost, self), mute_interval),
            'host/contracts' : Alert(super(Siahost, self), mute_interval),
            'host/storage' : Alert(super(Siahost, self), mute_interval)
        }

        accounting_cron = config_data.get_value_or_default('0 0 * * MON', 'accounting_interval')[0]

        self.__health = Siahealth(self, config_data)
        self.__storage = Siastorage(self)
        self.__wallet = Siawallet(self, config_data)
        self.__autoprice = None
        self.__reports = Siareports(self, self.__coinprice, accounting_cron)
        if 'autoprice' in  config_data.data:
            self.__autoprice = Siaautoprice(self, self.__api, self.__coinprice, config_data)
            scheduler.add_job(f'{name}-autoprice' ,self.price, config_data.get_value_or_default('0 0 * * *', 'price_interval')[0])

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('0 * * * *', 'check_interval')[0])
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-list', self.list, config_data.get_value_or_default('59 23 * * *', 'list_interval')[0])
        scheduler.add_job(f'{name}-accounting', self.accounting, accounting_cron)

    async def check(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None in (consensus, host, wallet):
            return
        
        self.__health.check(consensus, host, wallet)

    async def summary(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None in (consensus, host, storage, contracts, wallet):
            self.send(Plugin.Channel.info, 'No summary created, host is not available.')
            return

        await self.__coinprice.update()

        now = datetime.now()
        height = consensus.height
        recent_height = Siablocks.at_time(now - self.__recent_intervall, consensus)

        contracts_count = 0
        locked_collateral = 0
        risked_collateral = 0

        recent_started = 0
        recent_ended = 0
        failed_proofs = 0

        earnings = 0

        for contract in contracts.contracts:
            if contract.start > recent_height:
                recent_started += 1
            if contract.end > recent_height and contract.end <= height:
                recent_ended += 1
                if contract.proof_success:
                    earnings += contract.storage_revenue
                    earnings += contract.io_revenue
                    earnings += contract.ephemeral_revenue
                else:
                    failed_proofs += 1

            if contract.end <= height:
                continue
            contracts_count += 1
            locked_collateral += contract.locked_collateral
            risked_collateral += contract.risked_collateral

        self.__health.update_proof_deadlines(contracts)
        self.__health.summary(consensus, host, wallet)
        await self.__wallet.summary(wallet, locked_collateral, risked_collateral)
        self.__autoprice.summary(storage, wallet, locked_collateral)
        self.__storage.summary(storage)

        if contracts_count == 0:
            self.send(Plugin.Channel.debug, f'No contracts.')
            return

        self.send(Plugin.Channel.info, (f'{contracts_count} contracts\n'
            f'New contracts: {recent_started}\n'
            f'Ended contracts: {recent_ended}\n'
            f'Failed proofs: {failed_proofs}\n'
            f'Earnings: {round(earnings)} SC ({self.__coinprice.to_fiat(earnings)[0]} {self.__coinprice.currency})'))

    async def list(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))
        if None not in (consensus, host, storage, contracts, wallet):
            self.__health.update_proof_deadlines(contracts)

            height = consensus.height

            locked_collateral = 0
            risked_collateral = 0

            id = 0
            renderer = Tablerenderer(['ID', 'Size', 'Started', 'Ending', 'Locked', 'Storage', 'IO', 'Ephemeral'])
            data = renderer.data
            for contract in sorted(contracts.contracts, key=lambda x: x.end):
                if contract.end <= height:
                    continue

                locked_collateral += contract.locked_collateral
                risked_collateral += contract.risked_collateral

                data['ID'].append(f'{id}')
                data['Size'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.byte_to_auto(contract.datasize)))
                data['Started'].append(f'{Conversions.siablocks_to_duration(height - contract.start).days} d')
                data['Ending'].append(f'{Conversions.siablocks_to_duration(contract.end - height).days} d')
                data['Locked'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.locked_collateral)))
                data['Storage'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.storage_revenue)))
                data['IO'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.io_revenue)))
                data['Ephemeral'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(contract.ephemeral_revenue)))
                id += 1
            self.send(Plugin.Channel.debug, renderer.render())

            await self.__wallet.dump(wallet, locked_collateral, risked_collateral)
            self.__storage.report(storage)

    async def accounting(self):
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        if None not in (consensus, contracts):
            await self.__reports.accounting(consensus, contracts)

    async def price(self):
        if self.__autoprice is None:
            return
        consensus = await self.__request('consensus', lambda x: Siaconsensusdata(x))
        host = await self.__request('host', lambda x: Siahostdata(x))
        storage = await self.__request('host/storage', lambda x: Siastoragedata(x))
        contracts = await self.__request('host/contracts', lambda x: Siacontractsdata(x))
        wallet = await self.__request('wallet', lambda x: Siawalletdata(x))

        if None in (consensus, host, storage, contracts, wallet):
            return

        locked_collateral = 0
        for contract in contracts.contracts:
            if contract.end <= consensus.height:
                continue
            locked_collateral += contract.locked_collateral

        await self.__autoprice.update(host, storage, wallet, locked_collateral)

    async def __request(self, cmd, generator):
        alert = self.__request_alerts[cmd]
        async with self.__api.create_session() as session:
            try:
                json = await self.__api.get(session, cmd)
                result = generator(json)
                alert.reset(f'Request "{cmd}" is successful again.')
                return result
            except Exception as e:
                alert.send(f'Request "{cmd}" failed.')
                return None
