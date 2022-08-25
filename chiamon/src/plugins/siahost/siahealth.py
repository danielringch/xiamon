from ...core import Plugin, Alert

class Siahealth:
    def __init__(self, plugin, config):

        self.__plugin = plugin
        mute_interval, _ = config.get_value_or_default(24, 'alert_mute_interval')
        self.__minimum_available_balance, _ = config.get_value_or_default(10, 'minimum_available_balance')

        self.__unsync_alert = Alert(plugin, mute_interval)
        self.__wallet_locked_alert = Alert(plugin, mute_interval)
        self.__low_unlocked_balance_alert = Alert(plugin, mute_interval)

    async def check(self, consensus, host, wallet):
        if not consensus.synced:
            await self.__unsync_alert.send(f'Sia node is not synced, height {consensus.height}')
        else:
            await self.__unsync_alert.reset('Sia node is synced again.')

        if wallet.unlocked:
            await self.__wallet_locked_alert.reset('Wallet is unlocked again.')
        else:
            await self.__wallet_locked_alert.send('Wallet is locked.')

        free_balance = wallet.balance + wallet.pending
        locked_balance = host.lockedcollateral
        available_percent = 100 * free_balance / (free_balance + locked_balance)
        if available_percent < self.__minimum_available_balance:
            await self.__low_unlocked_balance_alert.send(f'Available balance is low: {available_percent:.0f} %')
        else:
            await self.__low_unlocked_balance_alert.reset('Available balance is above treshold again.')

    async def summary(self, consensus, host, wallet):
        message = (
            f'Synced: {consensus.synced} @{consensus.height}\n'
            f'Accepting contracts: {host.accepting}\n'
            f'Wallet unlocked: {wallet.unlocked}'
        )
        await self.__plugin.send(Plugin.Channel.info, message)
