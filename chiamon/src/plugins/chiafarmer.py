import asyncio
import datetime
from typing import DefaultDict, OrderedDict
import aiohttp
from ..core import Plugin, Alert, Chiarpc, Config

__version__ = "0.1.0"

class Chiafarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('chiafarmer', 'name')
        super(Chiafarmer, self).__init__(name, outputs)
        self.print(f'Chiafarmer plugin {__version__}; name: {name}')

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
        self.__threshold = float(config_data.get_value_or_default(0.99, 'underharvested_threshold')[0])

        self.__signage_points = Chiafarmer.SignagePoints(aggregation)

        self.__challenges = {}
        self.__recent_challenges = {}
        self.__failed_plots = set()
        self.__not_found_plots = set()

        scheduler.add_job(f'{name}-check' ,self.check, "*/10 * * * *")
        scheduler.add_job(f'{name}-summary', self.summary, config_data.get_value_or_default('0 0 * * *', 'summary_interval')[0])

    async def check(self):
        farmer_task = self.__check_farmer()
        harvester_task = self.__check_harvester()
        await asyncio.gather(farmer_task, harvester_task)

    async def summary(self):
        await self.send(Plugin.Channel.debug, 'Create summary.')
        factor, lowest_factor = self.__signage_points.get_harvest_factor()
        if factor is None:
            await self.send(Plugin.Channel.info, 'No harvest factor available, did not collect enough data for now.')
            return
        factor = factor * 100.0
        lowest_factor = lowest_factor * 100.0
        await self.send(Plugin.Channel.info, f'Average harvest factor | worst hour: {factor:.2f}% | {lowest_factor:.2f}%')

    async def __check_farmer(self):
        if self.__farmer_rpc is None:
            return
        await self.send(Plugin.Channel.debug, 'Checking farmer state.')
        async with aiohttp.ClientSession() as session:
            challenges = await self.__get_signage_points(session)
        if challenges is None:
            return
        self.__update_cached_challenges(challenges)
        await self.__evaluate_challenges()

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
        challenges = {}
        for sp in json['signage_points']:
            sp_data = sp['signage_point']
            challenge_id = sp_data['challenge_hash']
            challenge = challenges.setdefault(challenge_id, Chiafarmer.Challenge(challenge_id))
            challenge.signage_points[sp_data['signage_point_index']] = sp['proofs']
        return challenges

    def __update_cached_challenges(self, challenges):
        for id, challenge in challenges.items():
            if id in self.__recent_challenges:
                continue
            if id not in self.__challenges:
                _ = self.__challenges.setdefault(id, challenge)
            else:
                cached_challenge = self.__challenges[id]
                for sp_id, proofs in challenge.signage_points.items():
                    _ = cached_challenge.signage_points.setdefault(sp_id, proofs)
    
    async def __evaluate_challenges(self):
        if len(self.__challenges) == 0:
            return
        youngest_challenge = max(x.first_seen for x in self.__challenges.values())
        for id, challenge in list(self.__challenges.items()):
            if challenge.first_seen >= youngest_challenge:
                continue
            current_factor = self.__signage_points.add_challenge(len(challenge.signage_points))
            factor, _ = self.__signage_points.get_harvest_factor()
            try:
                if factor < self.__threshold:
                    await self.__underharvested_alert.send(f'Harvest rate is below treshold, factor={factor}')
            except TypeError:
                pass
            proofs = 0
            for sp_proofs in challenge.signage_points.values():
                proofs += len(sp_proofs)
                for sp_proof in sp_proofs:
                    await self.send(Plugin.Channel.debug, sp_proof)
            await self.send(Plugin.Channel.debug, f'Challenge {id} completed: harvest_factor={current_factor}, proofs={proofs}')
            del self.__challenges[id]
            self.__recent_challenges[id] = challenge.first_seen
            now = datetime.datetime.now()
            for recent_challenge_id, timestamp in list(self.__recent_challenges.items()):
                if now - timestamp > datetime.timedelta(hours=1):
                    del self.__recent_challenges[recent_challenge_id]

    async def __get_plots(self, session):
        json = await self.__harvester_rpc.post(session, 'get_plots')
        if json is None:
            return None, None
        failed = set(json['failed_to_open_filenames'])
        not_found = set(json['not_found_filenames'])
        return failed, not_found

    class Challenge:
        def __init__(self, id):
            self.first_seen = datetime.datetime.now()
            self.id = id
            self.signage_points = {}

    class SignagePoints:
        class ValueBundle:
            def __init__(self):
                self.actual = 0
                self.expected = 0

        def __init__(self, aggregation):
            self.__aggregation = aggregation
            self.__buckets = dict()

        def add_challenge(self, processed_signage_points):
            now = datetime.datetime.now()
            before_aggregation = now - datetime.timedelta(hours=self.__aggregation)
            bucket_id = int(now.strftime('%Y%m%d%H'))
            too_old_id = int(before_aggregation.strftime('%Y%m%d%H'))

            bucket = self.__buckets.setdefault(bucket_id, Chiafarmer.SignagePoints.ValueBundle())
            bucket.actual += processed_signage_points
            bucket.expected += 64

            for id in list(self.__buckets.keys()):
                if id <= too_old_id:
                    del self.__buckets[id]

            while len(self.__buckets) > self.__aggregation:
                self.__buckets.popitem()

            return processed_signage_points / 64.0

        def get_harvest_factor(self):
            if len(self.__buckets) < 2:
                return None, None

            factor = 0.0
            lowest_harvest_factor = 1.0
            count = 0

            for points in self.__buckets.values():
                current_factor = points.actual / float(points.expected)

                if current_factor < lowest_harvest_factor:
                    lowest_harvest_factor = current_factor

                factor += current_factor
                count += 1
            factor = factor / count

            return factor, lowest_harvest_factor


