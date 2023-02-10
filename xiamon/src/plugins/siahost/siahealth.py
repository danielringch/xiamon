from ...core import Plugin, Alert, Conversions

class Siahealth:
    def __init__(self, plugin, config):

        self.__plugin = plugin
        mute_interval = config.get(24, 'alert_mute_interval')
        self.__minimum_available_balance = config.get(10, 'minimum_available_balance')

        self.__unsync_alert = Alert(plugin, mute_interval)
        self.__wallet_locked_alert = Alert(plugin, mute_interval)
        self.__low_unlocked_balance_alert = Alert(plugin, mute_interval)
        self.__status_alert = Alert(plugin, mute_interval)

        self.__proof_deadlines = []

    def update_proof_deadlines(self, contracts):
        self.__proof_deadlines = sorted(x.end for x in contracts.contracts)

    def check(self, consensus, host, wallet):
        if not consensus.synced:
            self.__unsync_alert.send(f'Sia node is not synced, height {consensus.height}')
        else:
            self.__unsync_alert.reset('Sia node is synced again.')

        if wallet.unlocked:
            self.__wallet_locked_alert.reset('Wallet is unlocked again.')
        else:
            self.__wallet_locked_alert.send('Wallet is locked.')

        if wallet.balance < self.__minimum_available_balance:
            self.__low_unlocked_balance_alert.send(f'Available balance is low: {wallet.balance:.0f} SC')
        else:
            self.__low_unlocked_balance_alert.reset('Available balance is above treshold again.')

        if not host.statusok:
            self.__status_alert.send('Host seems to have connection issues.')
        else:
            self.__status_alert.reset('Host connection issues resolved.')

        block_diff = None
        for deadline in self.__proof_deadlines:
            if deadline < consensus.height:
                continue
            block_diff = deadline - consensus.height
            break
        if block_diff is not None:
            self.__plugin.msg.debug(f'Blocks until next proof: {block_diff} (~{Conversions.siablocks_to_duration(block_diff)} h)')

    def summary(self, consensus, host, wallet):
        self.__plugin.msg.info(f'{"S" if consensus.synced else "Not s"}ynced@{consensus.height}')
        if not host.accepting:
            self.__plugin.msg.info('Host does not accept contracts.')
        if not wallet.unlocked:
            self.__plugin.msg.info('Wallet is locked.')
