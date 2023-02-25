import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config, ApiRequestFailedException

class Chiaharvester(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name = config_data.get('chiaharvester', 'name')
        super(Chiaharvester, self).__init__(name, outputs)
        self.print(f'Plugin chiaharvester; name: {name}')

        self.__check_job = f'{name}-check'

        mute_interval = config_data.get(24, 'alert_mute_interval')

        self.__rpc = Chiarpc(
            config_data.get('127.0.0.1:8560', 'host'),
            config_data.data['cert'],
            config_data.data['key'],
            super(Chiaharvester, self))

        self.__plot_error_alert = Alert(super(Chiaharvester, self), mute_interval)

        self.__failed_plots = set()
        self.__not_found_plots = set()

        scheduler.add_job(self.__check_job ,self.check, config_data.get('*/5 * * * *', 'interval'))

    async def check(self):
        async with aiohttp.ClientSession() as session:
            failed, not_found = await self.__get_plots(session)
        if None in (failed, not_found):
            return
        failed_diff = failed - self.__failed_plots
        for failed_plot in failed_diff:
            self.__plot_error_alert.send(f'Failed to open plot: {failed_plot}')
        self.__failed_plots = failed

        not_found_diff = not_found - self.__not_found_plots
        for not_found_plot in not_found_diff:
            self.__plot_error_alert.send(f'Plot not found: {not_found_plot}')
        self.__not_found_plots = not_found

    async def __get_plots(self, session):
        try:
            json = await self.__rpc.post(session, 'get_plots')
        except ApiRequestFailedException:
            return None, None
        failed = set(json['failed_to_open_filenames'])
        not_found = set(json['not_found_filenames'])
        return failed, not_found
