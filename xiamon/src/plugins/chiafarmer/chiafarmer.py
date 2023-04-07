from datetime import timedelta
import aiohttp
from ...core import Plugin, Chiarpc, ApiRequestFailedException
from .challengecache import ChallengeCache

class Chiafarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Chiafarmer, self).__init__(config, outputs)

        self.__scheduler = scheduler
        self.__check_job = f'{self.name}-check'
        self.__evaluate_job = f'{self.name}-evaluate'
        self.__summary_job = f'{self.name}-summary'

        self.__farmer_rpc = Chiarpc(
            self.config.get('127.0.0.1:8559','host'),
            self.config.data['cert'],
            self.config.data['key'],
            super(Chiafarmer, self))

        self.__threshold_short = float(self.config.get(0.95, 'underharvested_threshold_short'))
        self.__threshold_long = float(self.config.get(0.99, 'underharvested_threshold_long'))

        self.__history = ChallengeCache(super(Chiafarmer, self))

        self.__scheduler.add_job(self.__check_job ,self.check, "*/5 * * * *")
        self.__scheduler.add_job(self.__evaluate_job, self.evaluate, "0 * * * *")
        self.__scheduler.add_job(self.__summary_job, self.summary, self.config.get('0 0 * * *', 'summary_interval'))
        self.__interval = self.__scheduler.get_current_interval(self.__summary_job)

    async def check(self):
        async with aiohttp.ClientSession() as session:
            await self.__get_signage_points(session)

    async def evaluate(self):
        factor_short = self.__history.get_factor(timedelta(hours=1))
        factor_long = self.__history.get_factor(self.__interval)

        if factor_short is not None:
            if factor_short < self.__threshold_short:
                self.msg.alert(f"Short time harvest factor is below treshold, factor={factor_short}.")
            else:
                self.msg.debug(f"Current harvest factor: {factor_short}.")

        if factor_long is not None:
            if factor_long < self.__threshold_long:
                self.alert('underharvested', f'Harvest factor is below treshold, factor={factor_long}.')
            else:
                self.reset_alert('underharvested', f'Harvest factor is above treshold again.')

    async def summary(self):
        factor = self.__history.get_factor(self.__interval)
        if factor is None:
            self.msg.info('No harvest factor available.')
        else:
            factor *= 100.0
            self.msg.info(f'Average harvest factor: {factor:.2f}%.')
        self.__history.cleanup()
        self.__interval = self.__scheduler.get_current_interval(self.__summary_job)

    async def __get_signage_points(self, session):
        try:
            json = await self.__farmer_rpc.post(session, 'get_signage_points')
        except ApiRequestFailedException:
            return
        for sp in json['signage_points']:
            sp_data = sp['signage_point']
            hash = sp_data['challenge_hash']
            index = sp_data['signage_point_index']
            self.__history.add_point(hash, index)
