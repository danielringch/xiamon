from ...core import Conversions, Tablerenderer

class Storjearning:
    def __init__(self, plugin, scheduler, database):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__db = database

    def summary(self, payout):
        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')

        earning = payout.current_month.storage_reward + \
            payout.current_month.egress_reward + \
            payout.current_month.repair_audit_reward - \
            payout.current_month.held_reward

        self.__db.update_balance(earning)
        last_earning = self.__db.get_balance(last_execution)

        if last_earning is None:
            self.__plugin.msg.info(f'Current month earnings: {earning:.2f} USD')
            return

        if earning < last_earning:
            delta_earning = earning
        else:
            delta_earning = earning - last_earning

        self.__plugin.msg.info(f'Current month earnings: {earning:.2f} USD (+ {delta_earning:.2f} USD)')
            
    def report(self, payout):
        storage_reward = payout.last_month.storage_reward
        egress_reward = payout.last_month.egress_reward
        repair_reward = payout.last_month.repair_audit_reward
        held_reward = payout.last_month.held_reward

        total_reward = storage_reward + egress_reward + repair_reward - held_reward

        storage = Conversions.byte_to_auto(payout.last_month.storage, binary=False)
        egress_traffic = Conversions.byte_to_auto(payout.last_month.egress_bandwidth, binary=False)
        repair_traffic = Conversions.byte_to_auto(payout.last_month.repair_audit_bandwidth, binary=False)

        storage_percent = storage_reward * 100.0 / (total_reward + held_reward)
        egress_percent = egress_reward * 100.0 / (total_reward + held_reward)
        repair_percent = repair_reward * 100.0 / (total_reward + held_reward)

        table = Tablerenderer([' ', 'Amount', 'Earnings', 'Percent'])

        table.data[' '].append('Storage')
        table.data[' '].append('Egress')
        table.data[' '].append('Repair/ Audit')
        table.data[' '].append('Held')
        table.data[' '].append('Total')

        table.data['Amount'].append(f'{storage[0]:.3f} {storage[1]}m')
        table.data['Amount'].append(f'{egress_traffic[0]:.3f} {egress_traffic[1]}')
        table.data['Amount'].append(f'{repair_traffic[0]:.3f} {repair_traffic[1]}')

        table.data['Earnings'].append(f'{storage_reward:.2f} USD')
        table.data['Earnings'].append(f'{egress_reward:.2f} USD')
        table.data['Earnings'].append(f'{repair_reward:.2f} USD')
        table.data['Earnings'].append(f'- {held_reward:.2f} USD')
        table.data['Earnings'].append(f'{total_reward:.2f} USD')

        table.data['Percent'].append(f'{storage_percent:.0f} %')
        table.data['Percent'].append(f'{egress_percent:.0f} %')
        table.data['Percent'].append(f'{repair_percent:.0f} %')

        self.__plugin.msg.report(table.render())
