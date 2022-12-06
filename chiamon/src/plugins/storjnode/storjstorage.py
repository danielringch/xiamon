from datetime import datetime
from ...core import Conversions

class Storjstorage:
    def __init__(self, plugin, scheduler, database):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__db = database

    def summary(self, node, payout):
        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')

        self.__print_storage(node)
        self.__print_bandwidth(node, payout, last_execution)

    def __print_storage(self, node):
        used_space = node.used_space
        total_space = node.total_space
        free_space = total_space - used_space - node.trash_space

        self.__db.update_storage(used_space)

        scaled_used_storage = Conversions.byte_to_auto(used_space, binary=False)
        scaled_total_storage = Conversions.byte_to_auto(node.total_space, binary=False)
        used_percent = (used_space / total_space) * 100

        self.__plugin.msg.info(f'Storage: {scaled_used_storage[0]:.3f} {scaled_used_storage[1]} '
                                f'of {scaled_total_storage[0]:.3f} {scaled_total_storage[1]} ' 
                                f'({used_percent:.2f} %)')

    def __print_bandwidth(self, node, payout, reference_time):
        upload, download, repair, duration = self.__get_traffic(node, payout, reference_time)

        if None in (download, upload, repair, duration):
            self.__plugin.msg.info('No traffic data available.')
            return

        scaled_upload = Conversions.byte_to_auto(upload, binary=False)
        scaled_up_bandwidth = Conversions.bit_to_auto(8 * upload / duration.total_seconds())
        scaled_download = Conversions.byte_to_auto(download, binary=False)
        scaled_down_bandwidth = Conversions.bit_to_auto(8 * download / duration.total_seconds())
        scaled_repair = Conversions.byte_to_auto(repair, binary=False)
        scaled_rep_bandwidth = Conversions.bit_to_auto(8 * repair / duration.total_seconds())
        self.__plugin.msg.info(
            f'Upload: {scaled_upload[0]:.3f} {scaled_upload[1]} ({scaled_up_bandwidth[0]:.3f} {scaled_up_bandwidth[1]}/s)\n'
            f'Download: {scaled_download[0]:.3f} {scaled_download[1]} ({scaled_down_bandwidth[0]:.3f} {scaled_down_bandwidth[1]}/s)\n'
            f'Repair: {scaled_repair[0]:.3f} {scaled_repair[1]} ({scaled_rep_bandwidth[0]:.3f} {scaled_rep_bandwidth[1]}/s)'
        )

    def __get_traffic(self, node, payout, reference_time):
        repair_audit_bandwidth = payout.current_month.repair_audit_bandwidth
        download_bandwidth = payout.current_month.egress_bandwidth
        upload_bandwidth = node.traffic - repair_audit_bandwidth - download_bandwidth

        self.__db.update_traffic(upload_bandwidth, download_bandwidth, repair_audit_bandwidth)

        last_upload, last_download, last_repair = self.__db.get_traffic(reference_time)

        if None in (last_upload, last_download, last_repair):
            self.__plugin.msg.debug(
                f'Can not calculate traffic: no old traffic data available.',
                f'Requested timestamp: {reference_time}')
            return None, None, None, None

        if (upload_bandwidth < last_upload) or (download_bandwidth < last_download) or (repair_audit_bandwidth < last_repair):
            self.__plugin.msg.debug(f'Can not calculate traffic: Change of month detected.')
            return None, None, None, None

        upload_delta = upload_bandwidth - last_upload
        download_delta = download_bandwidth - last_download
        repair_delta = repair_audit_bandwidth - last_repair

        return upload_delta, download_delta, repair_delta, (datetime.now() - reference_time)
