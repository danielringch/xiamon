from datetime import datetime, timedelta
from collections import namedtuple

from ...core import Plugin, Conversions, Tablerenderer
from .siablocks import Siablocks

class Siareports:

    RewardTypes = namedtuple("RewardTypes", "storage io ephemeral total fiat")

    def __init__(self, plugin, coinprice, scheduler):
        self.__plugin = plugin
        self.__coinprice = coinprice
        self.__scheduler = scheduler

    async def accounting(self, consensus, contracts):
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

    def __add_to_table(self, date, contracts, table):
        count = 0
        storage = 0
        io = 0
        ephemeral = 0
        for contract in contracts:
            count += 1
            storage += contract.storage_revenue
            io += contract.io_revenue
            ephemeral += contract.ephemeral_revenue
        total = storage + io + ephemeral
        fiat = self.__coinprice.to_fiat(total)
        table.data['Date'].append(date.strftime("%d.%m.%Y"))
        table.data['Contracts'].append(count)
        table.data['Storage'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(storage)))
        table.data['IO'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(io)))
        table.data['Ephemeral'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(ephemeral)))
        table.data['Sum'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(total)))
        table.data['Coinprice'].append(f'{self.__coinprice.price} {self.__coinprice.currency}/SC')
        table.data['Fiat'].append(f'{fiat:.2f} {self.__coinprice.currency}')
        return self.RewardTypes(storage, io, ephemeral, total, fiat)

    def __add_summary(self, table, rewards):
        total = rewards.storage + rewards.io + rewards.ephemeral

        table.data['Date'].append('Total')
        table.data['Contracts'].append('')
        table.data['Storage'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(rewards.storage)))
        table.data['IO'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(rewards.io)))
        table.data['Ephemeral'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(rewards.ephemeral)))
        table.data['Sum'].append('{x[0]:.0f} {x[1]}'.format(x=Conversions.siacoin_to_auto(rewards.total)))
        table.data['Coinprice'].append('')
        table.data['Fiat'].append(f'{rewards.fiat:.2f} {self.__coinprice.currency}')

        table.data['Date'].append('Percent')
        table.data['Contracts'].append('')
        table.data['Storage'].append(f'{(rewards.storage / rewards.total * 100):.0f} %')
        table.data['IO'].append(f'{(rewards.io / rewards.total * 100):.0f} %')
        table.data['Ephemeral'].append(f'{(rewards.ephemeral / rewards.total * 100):.0f} %')
        table.data['Sum'].append('')
        table.data['Coinprice'].append('')
        table.data['Fiat'].append('')
