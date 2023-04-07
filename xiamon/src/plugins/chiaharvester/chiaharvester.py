import aiohttp
from ...core import Plugin, Chiarpc, ApiRequestFailedException

class Chiaharvester(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chiaharvester, self).__init__(config, outputs)

        self.__check_job = f'{self.name}-check'

        self.__rpc = Chiarpc(
            self.config.get('127.0.0.1:8560', 'host'),
            self.config.data['cert'],
            self.config.data['key'],
            super(Chiaharvester, self))

        self.__failed_plots = set()
        self.__not_found_plots = set()

        scheduler.add_job(self.__check_job ,self.check, self.config.get('*/5 * * * *', 'interval'))

    async def check(self):
        async with aiohttp.ClientSession() as session:
            failed, not_found = await self.__get_plots(session)
        if None in (failed, not_found):
            return
        failed_diff = failed - self.__failed_plots
        for failed_plot in failed_diff:
            self.msg.alert(f'Failed to open plot: {failed_plot}')
        self.__failed_plots = failed

        not_found_diff = not_found - self.__not_found_plots
        for not_found_plot in not_found_diff:
            self.msg.alert(f'Plot not found: {not_found_plot}')
        self.__not_found_plots = not_found

    async def __get_plots(self, session):
        try:
            json = await self.__rpc.post(session, 'get_plots')
        except ApiRequestFailedException:
            return None, None
        failed = set(json['failed_to_open_filenames'])
        not_found = set(json['not_found_filenames'])
        return failed, not_found
