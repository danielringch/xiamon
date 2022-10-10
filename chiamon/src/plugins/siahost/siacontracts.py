from datetime import datetime, timedelta
from collections import namedtuple

from ...core import Plugin, Conversions, Tablerenderer
from .siablocks import Siablocks

class Siacontracts:

    RewardTypes = namedtuple("RewardTypes", "storage io ephemeral total fiat")

    def __init__(self, plugin, coinprice, scheduler, database):
        self.__plugin = plugin
        self.__coinprice = coinprice
        self.__scheduler = scheduler
        self.__db = database

    def summary(self, consensus, contracts, last_execution):
        messages = []
        height = consensus.height
        last_height = Siablocks.at_time(last_execution, consensus)

        active_contracts = 0
        recent_started = 0
        recent_ended = 0
        failed_proofs = 0

        settled_earnings = 0
        pending_storage_earnings = 0
        pending_io_earnings = 0
        pending_ephemeral_earnings = 0

        for contract in contracts.contracts:
            if contract.start > last_height:
                recent_started += 1
            if contract.end > last_height and contract.end <= height:
                recent_ended += 1
                if contract.proof_success:
                    settled_earnings += contract.storage_revenue
                    settled_earnings += contract.io_revenue
                    settled_earnings += contract.ephemeral_revenue
                else:
                    failed_proofs += 1

            if contract.end <= height:
                continue
            active_contracts += 1
            pending_storage_earnings += contract.storage_revenue
            pending_io_earnings += contract.io_revenue
            pending_ephemeral_earnings += contract.ephemeral_revenue
        
        self.__db.update_contracts(active_contracts, 
            round(pending_storage_earnings), 
            round(pending_io_earnings), 
            round(pending_ephemeral_earnings))

        _, last_pending_storage_earnings, last_pending_io_earnings, last_pending_ephemeral_earnings = \
            self.__db.get_contracts(last_execution)

        last_pending_earnings = last_pending_storage_earnings + last_pending_io_earnings + last_pending_ephemeral_earnings \
            if None not in (last_pending_storage_earnings, last_pending_io_earnings, last_pending_ephemeral_earnings) else None
        pendings_earnings = pending_storage_earnings + pending_io_earnings + pending_ephemeral_earnings

        messages.append(f'{active_contracts} contracts')
        messages.append(f'New contracts: {recent_started}')
        messages.append(f'Ended contracts: {recent_ended}')
        messages.append(f'Failed proofs: {failed_proofs}')
        messages.append(f'Settled earnings: {round(settled_earnings)} SC ({self.__coinprice.to_fiat_string(settled_earnings)})')
        if last_pending_earnings is not None:
            non_settled_earnings = pendings_earnings - last_pending_earnings
            messages.append(f'Non-settled earnings: {round(non_settled_earnings)} SC ({self.__coinprice.to_fiat_string(non_settled_earnings)})')
        messages.append(f'Non-settled balance: {round(pendings_earnings)} SC ({self.__coinprice.to_fiat_string(pendings_earnings)})')

        self.__plugin.send(Plugin.Channel.info, '\n'.join(messages))

    def contract_list(self, consensus, contracts):
        height = consensus.height
        id = 0
        renderer = Tablerenderer(['ID', 'Size', 'Started', 'Ending', 'Locked', 'Storage', 'IO', 'Ephemeral'])
        data = renderer.data
        for contract in sorted(contracts.contracts, key=lambda x: x.end):
            if contract.end <= height:
                continue

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

    def accounting(self, consensus, contracts):
        now = datetime.now()
        max_timestamp = now - timedelta(hours=1)
        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-accounting')
        if last_execution > max_timestamp:
            self.__plugin.send(Plugin.Channel.error, 'Accounting failed: unabled to calculate previous report time.')
            return

        table = Tablerenderer(['Date', 'Contracts', 'Storage', 'IO', 'Ephemeral', 'Sum', 'Coinprice', 'Fiat'])

        now = now.date()
        last_execution = last_execution.date()

        total_rewards = self.RewardTypes(0, 0, 0, 0, 0)

        while now > last_execution:
            yesterday = now - timedelta(days=1)
            day_rewards = self.__add_to_table(
                yesterday,
                self.__extract_contracts(
                    consensus, 
                    contracts, 
                    datetime.combine(yesterday, datetime.min.time()), 
                    datetime.combine(now, datetime.min.time())
                ),
                table
            )
            total_rewards = self.RewardTypes(
                total_rewards.storage + day_rewards.storage,
                total_rewards.io + day_rewards.io,
                total_rewards.ephemeral + day_rewards.ephemeral,
                total_rewards.total + day_rewards.total,
                total_rewards.fiat + day_rewards.fiat
            )

            now = yesterday

        table.reverse()

        self.__add_summary(table, total_rewards)

        self.__plugin.send(Plugin.Channel.report, table.render())


    def __extract_contracts(self, consensus, contracts, begin, end):
        begin_height = Siablocks.at_time(begin, consensus)
        end_height = Siablocks.at_time(end, consensus)

        return list(filter(lambda x: x.end >= begin_height and x.end < end_height, contracts.contracts))

    def __get_rewards(self, contracts):
        storage = sum(x.storage_revenue for x in contracts)
        io = sum(x.io_revenue for x in contracts)
        ephemeral = sum(x.ephemeral_revenue for x in contracts)
        total = storage + io + ephemeral
        fiat = self.__coinprice.to_fiat(total)

        return self.RewardTypes(storage, io, ephemeral, total, fiat)

    def __add_row(self, table, rewards):
        table.data['Storage'].append(f'{round(rewards.storage)} SC')
        table.data['IO'].append(f'{round(rewards.io)} SC')
        table.data['Ephemeral'].append(f'{round(rewards.ephemeral)} SC')
        table.data['Sum'].append(f'{round(rewards.total)} SC')
        table.data['Fiat'].append(f'{rewards.fiat:.2f} {self.__coinprice.currency}')

    def __add_to_table(self, date, contracts, table):
        rewards = self.__get_rewards(contracts)
        table.data['Date'].append(date.strftime("%d.%m.%Y"))
        table.data['Contracts'].append(len(contracts))
        table.data['Coinprice'].append(f'{self.__coinprice.price} {self.__coinprice.currency}/SC')
        self.__add_row(table, rewards)
        return rewards

    def __add_summary(self, table, rewards):
        table.data['Date'].append('Total')
        table.data['Contracts'].append('')
        table.data['Coinprice'].append('')
        self.__add_row(table, rewards)

        table.data['Date'].append('Percent')
        table.data['Contracts'].append('')
        table.data['Storage'].append(f'{(rewards.storage / rewards.total * 100):.0f} %')
        table.data['IO'].append(f'{(rewards.io / rewards.total * 100):.0f} %')
        table.data['Ephemeral'].append(f'{(rewards.ephemeral / rewards.total * 100):.0f} %')
        table.data['Sum'].append('')
        table.data['Coinprice'].append('')
        table.data['Fiat'].append('')
