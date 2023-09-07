from datetime import datetime
from statistics import mean
from ...core import Conversions, Tablerenderer

class Storjstorage:
    def __init__(self, plugin, scheduler, database):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__db = database

    def summary(self, node, payout):
        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')

        self.__print_storage(node)
        self.__print_traffic(node, payout, last_execution)

    def __print_storage(self, node_data):
        total_used = 0
        total_total = 0
        verbose_table = Tablerenderer(['Node', 'Used', 'Total', 'Percent'])
        for node, one_node_data in node_data.items():
            used_space = one_node_data.used_space
            total_space = one_node_data.total_space
            total_used += used_space
            total_total += total_space

            self.__db.update_storage(node.id, used_space)

            scaled_used_storage = Conversions.byte_to_auto(used_space, binary=False)
            scaled_total_storage = Conversions.byte_to_auto(total_space, binary=False)
            verbose_table.add_row((node.name,
                                   f'{scaled_used_storage[0]:.3f} {scaled_used_storage[1]}',
                                   f'{scaled_total_storage[0]:.3f} {scaled_total_storage[1]}',
                                   f'{((used_space / total_space) * 100):.2f} %'))
        self.__plugin.msg.verbose('Storage:')
        self.__plugin.msg.verbose(verbose_table.render())

        scaled_total_used_storage = Conversions.byte_to_auto(total_used, binary=False)
        scaled_total_total_storage = Conversions.byte_to_auto(total_total, binary=False)

        self.__plugin.msg.info(f'Storage: {scaled_total_used_storage[0]:.3f} {scaled_total_used_storage[1]} '
                                f'of {scaled_total_total_storage[0]:.3f} {scaled_total_total_storage[1]} ' 
                                f'({((total_used / total_total) * 100):.2f} %)')

    def __print_traffic(self, node_data, payout_data, reference_time):
        uploads = {}
        downloads = {}
        repairs = {}
        durations = []
        traffic_incomplete = False

        for node, one_node_data in node_data.items():
            upload, download, repair, duration = self.__get_traffic(node, one_node_data, payout_data[node], reference_time)
            if None in (download, upload, repair, duration):
                traffic_incomplete = True
                continue
            uploads[node.name] = upload
            downloads[node.name] = download
            repairs[node.name] = repair
            durations.append(duration.total_seconds())

        duration = mean(durations) if len(durations) > 0 else 0

        self.__print_node_traffic('Upload:', uploads, duration)
        self.__print_node_traffic('Download:', downloads, duration)
        self.__print_node_traffic('Repair:', repairs, duration)

        if traffic_incomplete:
            self.__plugin.msg.info(f'No traffic data available.')
            return

        scaled_upload, scaled_up_bandwidth = self.__scale(sum(uploads.values()), duration)
        scaled_download, scaled_down_bandwidth = self.__scale(sum(downloads.values()), duration)
        scaled_repair, scaled_rep_bandwidth = self.__scale(sum(repairs.values()), duration)

        self.__plugin.msg.info(
            f'Upload: {scaled_upload[0]:.3f} {scaled_upload[1]} ({scaled_up_bandwidth[0]:.3f} {scaled_up_bandwidth[1]}/s)')
        self.__plugin.msg.info(
            f'Download: {scaled_download[0]:.3f} {scaled_download[1]} ({scaled_down_bandwidth[0]:.3f} {scaled_down_bandwidth[1]}/s)')
        self.__plugin.msg.info(
            f'Repair: {scaled_repair[0]:.3f} {scaled_repair[1]} ({scaled_rep_bandwidth[0]:.3f} {scaled_rep_bandwidth[1]}/s)')

    def __print_node_traffic(self, header, traffics, duration):
        verbose_table = Tablerenderer(['Node', 'Traffic', 'Bandwidth'])
        for host, traffic in traffics.items():
            scaled_traffic, scaled_bandwidth = self.__scale(traffic, duration)
            verbose_table.add_row((host, f'{scaled_traffic[0]:.3f} {scaled_traffic[1]}', f'{scaled_bandwidth[0]:.3f} {scaled_bandwidth[1]}/s'))
        self.__plugin.msg.verbose(header)
        self.__plugin.msg.verbose(verbose_table.render())

    def __get_traffic(self, node, node_data, payout_data, reference_time):
        repair_audit_bandwidth = payout_data.current_month.repair_audit_bandwidth
        download_bandwidth = payout_data.current_month.egress_bandwidth
        upload_bandwidth = node_data.traffic - repair_audit_bandwidth - download_bandwidth

        self.__db.update_traffic(node.id, upload_bandwidth, download_bandwidth, repair_audit_bandwidth)

        last_upload, last_download, last_repair = self.__db.get_traffic(node.id, reference_time)

        if None in (last_upload, last_download, last_repair):
            self.__plugin.msg.debug(
                f'Can not calculate traffic: no old traffic data for node {node.name} available. ',
                f'Requested timestamp: {reference_time}')
            return None, None, None, None

        if (upload_bandwidth < last_upload) or (download_bandwidth < last_download) or (repair_audit_bandwidth < last_repair):
            self.__plugin.msg.debug(f'Can not calculate traffic for node {node.name}: Change of month detected.')
            return None, None, None, None

        upload_delta = upload_bandwidth - last_upload
        download_delta = download_bandwidth - last_download
        repair_delta = repair_audit_bandwidth - last_repair

        return upload_delta, download_delta, repair_delta, (datetime.now() - reference_time)
    
    @staticmethod
    def __scale(traffic, duration):
        scaled_traffic = Conversions.byte_to_auto(traffic, binary=False)
        try:
            scaled_bandwidth = Conversions.bit_to_auto(8 * traffic / duration)
        except ZeroDivisionError:
            scaled_bandwidth = 0
        return scaled_traffic, scaled_bandwidth
