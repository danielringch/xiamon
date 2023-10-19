from ...core import Conversions

class Hostdstorage:
    def __init__(self, plugin):
        self.__plugin = plugin

    def summary(self, metrics, last_metrics):
        used = Conversions.byte_to_auto(metrics.used_storage, binary=False)
        total = Conversions.byte_to_auto(metrics.total_storage, binary=False)
        self.__plugin.msg.info(f'Total storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]}')
        self.__plugin.msg.info(f'Total usage: {(100.0 * metrics.used_storage / metrics.total_storage):.1f} %')

        self.__plugin.msg.info(self.__get_traffic_message(metrics, last_metrics))

    def __get_traffic_message(self, metrics, last_metrics):
        ingress, egress, duration = self.__get_traffic(metrics, last_metrics)

        scaled_download = Conversions.byte_to_auto(ingress, binary=False)
        scaled_down_bandwidth = Conversions.bit_to_auto(8 * ingress / duration.total_seconds())
        scaled_upload = Conversions.byte_to_auto(egress, binary=False)
        scaled_up_bandwidth = Conversions.bit_to_auto(8 * egress / duration.total_seconds())
        return (
            f'Ingress: {scaled_download[0]:.2f} {scaled_download[1]} ({scaled_down_bandwidth[0]:.2f} {scaled_down_bandwidth[1]}/s)\n'
            f'Egress: {scaled_upload[0]:.2f} {scaled_upload[1]} ({scaled_up_bandwidth[0]:.2f} {scaled_up_bandwidth[1]}/s)'
        )

    def __get_traffic(self, metrics, last_metrics):
        ingress = metrics.ingress - last_metrics.ingress
        egress = metrics.egress - last_metrics.egress

        return ingress, egress, (metrics.timestamp - last_metrics.timestamp)
