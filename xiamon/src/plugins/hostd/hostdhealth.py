

class Hostdhealth:
    def __init__(self, plugin, config):

        self.__plugin = plugin
        self.__minimum_available_balance = config.get(10, 'minimum_available_balance')

    def check(self, consensus, wallet):
        if not consensus.synced:
            self.__plugin.alert('unsync', f'Sia node is not synced, height {consensus.height}')
        else:
            self.__plugin.reset_alert('unsync', 'Sia node is synced again.')

        if wallet.balance < self.__minimum_available_balance:
            self.__plugin.alert('balance', f'Available balance is low: {wallet.balance:.0f} SC')
        else:
            self.__plugin.reset_alert('balance', 'Available balance is above treshold again.')

    def summary(self, consensus):
        self.__plugin.msg.info(f'{"S" if consensus.synced else "Not s"}ynced@{consensus.height}')
