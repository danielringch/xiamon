from ...core import Conversions

class Siahealth:
    def __init__(self, plugin, config):

        self.__plugin = plugin
        self.__minimum_available_balance = config.get(10, 'minimum_available_balance')

        self.__proof_deadlines = []

    def update_proof_deadlines(self, contracts):
        self.__proof_deadlines = sorted(x.end for x in contracts.contracts)

    def check(self, consensus, host, wallet):
        if not consensus.synced:
            self.__plugin.alert('unsync', f'Sia node is not synced, height {consensus.height}')
        else:
            self.__plugin.reset_alert('unsync', 'Sia node is synced again.')

        if wallet.unlocked:
            self.__plugin.reset_alert('locked', 'Wallet is unlocked again.')
        else:
            self.__plugin.alert('locked', 'Wallet is locked.')

        if wallet.balance < self.__minimum_available_balance:
            self.__plugin.alert('balance', f'Available balance is low: {wallet.balance:.0f} SC')
        else:
            self.__plugin.reset_alert('balance', 'Available balance is above treshold again.')

        if not host.statusok:
            self.__plugin.alert('connection', 'Host seems to have connection issues.')
        else:
            self.__plugin.reset_alert('connection', 'Host connection issues resolved.')

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
