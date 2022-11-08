from datetime import datetime
from ...core import Plugin, Conversions

class Siastorage:
    def __init__(self, plugin, scheduler, database):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__db = database

    def summary(self, storage, traffic):
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        self.__plugin.msg.info(f'Total storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]}')
        self.__plugin.msg.info(f'Total usage: {(100 * storage.used_space / storage.total_space):.1f} %')

        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')
        self.__plugin.msg.info(self.__get_traffic_message(traffic, last_execution))

    def report(self, storage, traffic):
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        usage_percent = 100 * storage.used_space / storage.total_space
        self.__plugin.msg.report(f'Storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]} ({usage_percent:.2f} %)')

        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-list')
        self.__plugin.msg.report(self.__get_traffic_message(traffic, last_execution))

    def __get_traffic_message(self, traffic, reference_time):
        download, upload, duration = self.__get_traffic(traffic, reference_time)

        if None in (download, upload, duration):
            return 'No traffic data available.'

        scaled_download = Conversions.byte_to_auto(download, binary=False)
        scaled_down_bandwidth = Conversions.bit_to_auto(8 * download / duration.total_seconds())
        scaled_upload = Conversions.byte_to_auto(upload, binary=False)
        scaled_up_bandwidth = Conversions.bit_to_auto(8 * upload / duration.total_seconds())
        return (
            f'Download: {scaled_download[0]:.2f} {scaled_download[1]} ({scaled_down_bandwidth[0]:.2f} {scaled_down_bandwidth[1]}/s)\n'
            f'Upload: {scaled_upload[0]:.2f} {scaled_upload[1]} ({scaled_up_bandwidth[0]:.2f} {scaled_up_bandwidth[1]}/s)'
        )

    def __get_traffic(self, traffic, reference_time):
        current_epoch = str(traffic.start)
        self.__db.update_traffic(current_epoch, traffic.upload, traffic.download)
        last_epoch, last_upload, last_download = self.__db.get_traffic(reference_time)

        if None in (last_epoch, last_upload, last_download):
            self.__plugin.msg.debug(
                f'Can not calculate traffic: no old traffic data available.',
                f'Requested timestamp: {reference_time}')
            return None, None, None

        if current_epoch != last_epoch:
            self.__plugin.msg.debug(
                f'Can not calculate traffic: Sia was restarted since last traffic data.',
                f'Last data: {reference_time}, epoch {last_epoch}',
                f'Current epoch {current_epoch}')
            return None, None, None

        download = traffic.download - last_download
        upload = traffic.upload - last_upload

        return download, upload, (datetime.now() - reference_time)
