from ...core import Conversions, Tablerenderer, Storjpayoutdata

class Storjearning:
    def __init__(self, plugin, scheduler, database, csv):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__db = database
        self.__csv = csv

    def summary(self, payouts):
        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')

        verbose_table = Tablerenderer(['Node', 'Earning', 'Delta'])
        total_earning = 0
        total_delta_earning = 0
        total_delta_earning_incomplete = False

        for host, payout in payouts.items():
            earning = self.__get_total_reward(payout.current_month.storage_reward,
                                              payout.current_month.egress_reward,
                                              payout.current_month.repair_audit_reward,
                                              payout.current_month.held_reward)
            
            self.__db.update_balance(host.id, earning)

            total_earning += earning

            last_earning = self.__db.get_balance(host.id, last_execution)
            if last_earning is None:
                verbose_table.add_row((host.name, f'{earning:.2f} USD', ''))
                total_delta_earning_incomplete = True
                continue

            if earning < last_earning:
                delta_earning = earning
            else:
                delta_earning = earning - last_earning
            verbose_table.add_row((host.name, f'{earning:.2f} USD', f'{delta_earning:.2f} USD'))
            total_delta_earning += delta_earning

        self.__plugin.msg.verbose('Earnings:')
        self.__plugin.msg.verbose(verbose_table.render())

        if total_delta_earning_incomplete:
            self.__plugin.msg.info(f'Current month earnings: {total_earning:.2f} USD')
            return

        self.__plugin.msg.info(f'Current month earnings: {total_earning:.2f} USD (+ {total_delta_earning:.2f} USD)')
            
    def accounting(self, payouts):
        total_disk_space = 0
        total_egress_bandwidth = 0
        total_egress_repair_audit = 0
        total_disk_space_payout = 0
        total_egress_bandwidth_payout = 0
        total_egress_repair_audit_payout = 0
        total_held = 0

        for host, payout in payouts.items():
            payout = payout.last_month
            total_disk_space += payout.storage
            total_egress_bandwidth += payout.egress_bandwidth
            total_egress_repair_audit += payout.repair_audit_bandwidth
            total_disk_space_payout += payout.storage_reward
            total_egress_bandwidth_payout += payout.egress_reward
            total_egress_repair_audit_payout += payout.repair_audit_reward
            total_held += payout.held_reward

            self.__write_accounting_table(f'Node {host.name}', payout)

        total_data = {
            'diskSpace': total_disk_space,
            'egressBandwidth': total_egress_bandwidth,
            'egressRepairAudit': total_egress_repair_audit,
            'diskSpacePayout': total_disk_space_payout * 100.0,
            'egressBandwidthPayout': total_egress_bandwidth_payout * 100.0,
            'egressRepairAuditPayout': total_egress_repair_audit_payout * 100.0,
            'held': total_held * 100.0
        }

        self.__write_accounting_table('Total', Storjpayoutdata.Month(total_data))

        self.__csv.add_line({
            'Storage reward (USD)': total_disk_space_payout,
            'Egress reward (USD)': total_egress_bandwidth_payout,
            'Repair/ audit reward (USD)': total_egress_repair_audit_payout,
            'Held reward (USD)': total_held * -1,
            'Total reward (USD)': self.__get_total_reward(total_disk_space_payout,
                                                          total_egress_bandwidth_payout,
                                                          total_egress_repair_audit_payout,
                                                          total_held)
        })


    def __write_accounting_table(self, header, data):
        storage_reward = data.storage_reward
        egress_reward = data.egress_reward
        repair_reward = data.repair_audit_reward
        held_reward = data.held_reward

        total_reward = self.__get_total_reward(storage_reward, egress_reward, repair_reward, held_reward)

        storage = Conversions.byte_to_auto(data.storage, binary=False)
        egress_traffic = Conversions.byte_to_auto(data.egress_bandwidth, binary=False)
        repair_traffic = Conversions.byte_to_auto(data.repair_audit_bandwidth, binary=False)

        try:
            storage_percent = storage_reward * 100.0 / (total_reward + held_reward)
            egress_percent = egress_reward * 100.0 / (total_reward + held_reward)
            repair_percent = repair_reward * 100.0 / (total_reward + held_reward)
        except ZeroDivisionError:
            storage_percent = 0
            egress_percent = 0
            repair_percent = 0

        table = Tablerenderer([' ', 'Amount', 'Earnings', 'Percent'])

        table.add_row(('Storage', f'{storage[0]:.3f} {storage[1]}m', f'{storage_reward:.2f} USD', f'{storage_percent:.0f} %'))
        table.add_row(('Egress', f'{egress_traffic[0]:.3f} {egress_traffic[1]}', f'{egress_reward:.2f} USD', f'{egress_percent:.0f} %'))
        table.add_row(('Repair/ Audit', f'{repair_traffic[0]:.3f} {repair_traffic[1]}', f'{repair_reward:.2f} USD', f'{repair_percent:.0f} %'))
        table.add_row(('Held', '', f'- {held_reward:.2f} USD', ''))
        table.add_row(('Total', '', f'{total_reward:.2f} USD', ''))

        self.__plugin.msg.accounting(header)
        self.__plugin.msg.accounting(table.render())

    @staticmethod
    def __get_total_reward(storage, egress, repair, held):
        return storage + egress + repair - held
