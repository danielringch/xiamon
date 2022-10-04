from copy import deepcopy
from datetime import datetime, timedelta
from ...core import Plugin, Conversions

class Siastorage:
    def __init__(self, plugin, scheduler):
        self.__plugin = plugin
        self.__scheduler = scheduler
        self.__traffic_history = {}

    def summary(self, storage, traffic):
        message = []
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        message.append(f'Total storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]}')
        message.append(f'Total usage: {(100 * storage.used_space / storage.total_space):.1f} %')

        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-summary')
        message.append(self.__get_traffic_message(traffic, last_execution))
        
        self.__plugin.send(Plugin.Channel.info, '\n'.join(message))

    def report(self, storage, traffic):
        message = []
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        usage_percent = 100 * storage.used_space / storage.total_space
        message.append(f'Storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]} ({usage_percent:.2f} %)')

        last_execution = self.__scheduler.get_last_execution(f'{self.__plugin.name}-list')
        message.append(self.__get_traffic_message(traffic, last_execution))

        self.__plugin.send(Plugin.Channel.report, '\n'.join(message))

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
        now = datetime.now()
        self.__traffic_history[now] = traffic
        if len(self.__traffic_history) > 10:
            self.__traffic_history.popitem()

        class x:
            def __init__(self, y):
                self.start = y
                self.download = 0
                self.upload = 0

        self.__traffic_history[reference_time] = x(traffic.start)

        last_traffic = None
        duration = None
        for timestamp, payload in self.__traffic_history.items():
            if abs(timestamp - reference_time) < timedelta(minutes=5):
                last_traffic = payload
                duration = now - timestamp
                break

        if last_traffic is None or last_traffic.start != traffic.start:
            return None, None, None

        download = traffic.download - last_traffic.download
        upload = traffic.upload - last_traffic.upload

        return download, upload, duration
