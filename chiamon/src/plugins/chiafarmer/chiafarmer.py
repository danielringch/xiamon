import asyncio, datetime, os, re
from typing import DefaultDict, OrderedDict
import aiohttp
from ...core import Plugin, Alert, Chiarpc, Config
from .challengecache import ChallengeCache

class Chiafarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chiafarmer', 'name')
        super(Chiafarmer, self).__init__(name, outputs)
        self.print(f'Plugin chiafarmer; name: {name}')

        aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        farmer_host, _ = config_data.get_value_or_default('127.0.0.1:8559','farmer_host')
        harvester_host, _ = config_data.get_value_or_default('127.0.0.1:8560', 'harvester_host')
        self.__farmer_rpc = Chiarpc(farmer_host, config_data.data['farmer_cert'], config_data.data['farmer_key'],
            super(Chiafarmer, self), mute_interval) if farmer_host is not None else None
        self.__harvester_rpc = Chiarpc(harvester_host, config_data.data['harvester_cert'], config_data.data['harvester_key'],
            super(Chiafarmer, self), mute_interval) if harvester_host is not None else None

        self.__plot_error_alert = Alert(super(Chiafarmer, self), None)
        self.__underharvested_alert = Alert(super(Chiafarmer, self), mute_interval)
        self.__threshold_short = float(config_data.get_value_or_default(0.95, 'underharvested_threshold_short')[0])
        self.__threshold_long = float(config_data.get_value_or_default(0.99, 'underharvested_threshold_long')[0])

        db_path = os.path.join(config_data.data['db'], f"{re.sub('[^a-zA-Z0-9]+', '', name)}.yaml")
        self.__history = ChallengeCache(super(Chiafarmer, self), db_path, aggregation)

        self.__failed_plots = set()
        self.__not_found_plots = set()

        scheduler.add_job(f'{name}-check' ,self.check, "*/5 * * * *")
        scheduler.add_job(f'{name}-evaluate', self.evaluate, "0 * * * *")
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        farmer_task = self.__check_farmer()
        harvester_task = self.__check_harvester()
        await asyncio.gather(farmer_task, harvester_task)

    async def evaluate(self):
        await self.__history.cleanup()
        factor_short = self.__history.get_factor(whole_day=False)
        factor_long = self.__history.get_factor(whole_day=True)
        await self.__history.save()

        if factor_short is not None:
            if factor_short < self.__threshold_short:
                await self.send(Plugin.Channel.alert, f"Short time harvest factor is below treshold, factor={factor_short}.")
            else:
                await self.send(Plugin.Channel.debug, f"Current harvest factor: {factor_short}.")

        if factor_long is not None:
            if factor_long < self.__threshold_long:
                await self.__underharvested_alert.send(f'Harvest factor is below treshold, factor={factor_long}.')
            else:
                await self.__underharvested_alert.reset(f'Harvest factor is above treshold again.')

    async def summary(self):
        await self.send(Plugin.Channel.debug, 'Create summary.')
        factor = self.__history.get_factor()
        if factor is None:
            await self.send(Plugin.Channel.info, 'No harvest factor available.')
        else:
            factor *= 100.0
            await self.send(Plugin.Channel.info, f'Average harvest factor: {factor:.2f}%.')

    async def __check_farmer(self):
        if self.__farmer_rpc is None:
            return
        await self.send(Plugin.Channel.debug, 'Checking farmer state.')
        async with aiohttp.ClientSession() as session:
            await self.__get_signage_points(session)

    async def __check_harvester(self):
        if self.__harvester_rpc is None:
            return
        await self.send(Plugin.Channel.debug, 'Checking harvester.')
        async with aiohttp.ClientSession() as session:
            failed, not_found = await self.__get_plots(session)
        if failed is None:
            return
        failed_diff = failed - self.__failed_plots
        for failed_plot in failed_diff:
            await self.__plot_error_alert.send(f'Failed to open plot: {failed_plot}')
        self.__failed_plots = failed

        not_found_diff = not_found - self.__not_found_plots
        for not_found_plot in not_found_diff:
            await self.__plot_error_alert.send(f'Plot not found: {not_found_plot}')
        self.__not_found_plots = not_found

    async def __get_signage_points(self, session):
        json = await self.__farmer_rpc.post(session, 'get_signage_points')
        if json is None:
            return None
        for sp in json['signage_points']:
            sp_data = sp['signage_point']
            hash = sp_data['challenge_hash']
            index = sp_data['signage_point_index']
            self.__history.add_point(hash, index)

    async def __get_plots(self, session):
        json = await self.__harvester_rpc.post(session, 'get_plots')
        if json is None:
            return None, None
        failed = set(json['failed_to_open_filenames'])
        not_found = set(json['not_found_filenames'])
        return failed, not_found
