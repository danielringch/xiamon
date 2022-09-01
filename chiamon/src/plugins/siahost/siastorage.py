from ...core import Plugin, Conversions

class Siastorage:
    def __init__(self, plugin):
        self.__plugin = plugin

    def summary(self, storage):
        message = []
        for folder in storage.folders:
            used = Conversions.byte_to_auto(folder.used_space, binary=False)
            total = Conversions.byte_to_auto(folder.total_space, binary=False)
            message.append(f'{folder.path}: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]}')
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        message.append(f'Total storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]}')
        message.append(f'Total usage: {(100 * storage.used_space / storage.total_space):.1f} %')
        
        self.__plugin.send(Plugin.Channel.info, '\n'.join(message))

    def report(self, storage):
        used = Conversions.byte_to_auto(storage.used_space, binary=False)
        total = Conversions.byte_to_auto(storage.total_space, binary=False)
        usage_percent = 100 * storage.used_space / storage.total_space
        self.__plugin.send(Plugin.Channel.report, f'Storage: {used[0]:.2f} {used[1]} of {total[0]:.2f} {total[1]} ({usage_percent:.2f} %)')