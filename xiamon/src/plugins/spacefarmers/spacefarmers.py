import asyncio, aiohttp, datetime
from ...core import Plugin, Conversions
from .spacefarmersworker import SpacefarmersWorker

class Spacefarmers(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Spacefarmers, self).__init__(config, outputs)

        self.__scheduler = scheduler
        self.__startup_job = f'{self.name}-startup'
        self.__summary_job = f'{self.name}-summary'
        self.__check_job = f'{self.name}-check'
        scheduler.add_job(self.__summary_job ,self.summary, self.config.get('0 * * * *', 'summary_interval'))
        scheduler.add_job(self.__check_job, self.check, self.config.get('0 0 * * *', 'check_interval'))
        scheduler.add_startup_job(self.__startup_job, self.startup)

        self.__launcher_id = self.config.data['launcher_id']

        self.__workers = []
        for worker_name, worker_settings in self.config.data['harvesters'].items():
            self.__workers.append(SpacefarmersWorker(worker_name, float(worker_settings['maximum_offline_time'])))

        self.__last_check = scheduler.get_last_execution(self.__summary_job)

        self.__timeout = aiohttp.ClientTimeout(total=30)

    async def startup(self):
        async with aiohttp.ClientSession() as session:
            # offline tolerance might be longer than time since last summary,
            # so for correct offline detection, this extra check is necessary
            offline_check_duration = max(x.maximum_offline for x in self.__workers)
            partials, _ = await self.__get_partials(session, datetime.datetime.now() - offline_check_duration)
            for worker in self.__workers:
                worker.update(partials, no_stats=True)

            await self.__update_workers(session)

    async def summary(self):
        last_summary = self.__scheduler.get_last_execution(self.__summary_job)
        async with aiohttp.ClientSession() as session:
            stats_task = self.__get_stats(session)
            workers_task = self.__update_workers(session)
            earnings_task = self.__get_earnings(session, last_summary)
            stats, workers, earnings = await asyncio.gather(stats_task, workers_task, earnings_task)
        points = stats[0]
        netspace = stats[1]
        if None not in (points, netspace):
            self.msg.info(f'24h netspace: {netspace:.2f} TiB, {points} points')
        else:
            self.msg.info('No netspace information available.')
        if earnings is not None:
            self.msg.info(f'Earnings: {earnings} XCH')
        else:
            self.msg.info('No earnings information available.')
        if workers is not None:
            for worker in self.__workers:
                self.msg.info(
                    f'Harvester {worker.name} ({"online" if worker.online else "offline"}):',
                    f'Partials (valid | invalid): {worker.partials_valid} | {worker.partials_invalid}',
                    f'Avg. partial time: {worker.average_time:.1f} s'
                )
        else:
            self.msg.info('No harvester information available.')
        for worker in self.__workers:
            worker.reset_statistics()

    async def check(self):
        async with aiohttp.ClientSession() as session:
            await self.__update_workers(session)
            for worker in self.__workers:
                if not worker.online:
                    self.alert(f'worker_{worker.name}', f'Harvester {worker.name} is offline, latest partial receceived at {worker.latest_partial_timestamp}.')
                    continue
                self.reset_alert(f'worker_{worker.name}', f'Harvester {worker.name} is online again.')

    async def __get_stats(self, session):
        data = await self.__get(session, '')
        if data is None:
            return None, None
        return data['attributes']['points_24h'], data['attributes']['tib_24h']

    async def __update_workers(self, session):
        partials, newest_partial  = await self.__get_partials(session, self.__last_check)
        if partials is None:
            return None

        for worker in self.__workers:
            worker.update(partials)

        # since partials with yet unknown status are ignored when calculating the newest partial,
        # they will be queried again in the next update
        self.__last_check = newest_partial

        self.msg.debug(f'{len(partials)} new partials since last check.')

        return 0

    async def __get_partials(self, session, since):
        page = 1
        partials = []
        done = False
        newest_partial = since
        while not done:
            data = await self.__get(session, 'partials', {'page': page})
            if data is None:
                return None, None
            if len(data) == 0:
                done = True
            for raw_partial in data:
                partial = Spacefarmers.Partial(raw_partial['attributes'])
                if partial.valid is None:
                    continue
                if partial.timestamp > newest_partial:
                    newest_partial = partial.timestamp
                if partial.timestamp < since:
                    done = True
                    break
                partials.append(partial)
            page += 1
        return partials, newest_partial

    async def __get_earnings(self, session, since):
        earnings = 0
        page = 1
        done = False
        while not done:
            data = await self.__get(session, 'payouts', {'page': page})
            if data is None:
                return None
            if len(data) == 0:
                done = True
            for raw_payment in data:
                payment = raw_payment['attributes']
                if payment['coin'] != 'XCH':
                    continue
                if datetime.datetime.fromtimestamp(payment['timestamp']) < since:
                    done = True
                    break
                earnings += payment['amount']
            page += 1
        return Conversions.mojo_to_xch(earnings)

    async def __get(self, session, cmd, params = {}):
        data = {}
        try:
            request = f'https://www.spacefarmers.io/api/farmers/{self.__launcher_id}/{cmd}'
            async with session.get(request, params=params, timeout=self.__timeout) as response:
                response.raise_for_status()
                data =  await response.json()
        except asyncio.TimeoutError as e_timeout:
            self.alert(f'cmd_{cmd}', f'Request {cmd}: timeout')
            return None
        except Exception as e:
            self.alert(f'cmd_{cmd}', f'Request {cmd}: {repr(e)}')
            return None
        self.reset_alert(f'cmd_{cmd}', f'Request {cmd} successful again.')
        return data['data']

    class Partial:
        def __init__(self, json):
            self.harvester = json['harvester_id']
            self.timestamp = datetime.datetime.fromtimestamp(json['timestamp'])
            self.valid = self.get_valid(json['error_code'])
            self.time = json['time_taken'] / 1000.0 if json['time_taken'] is not None else None

        @staticmethod
        def get_valid(value):
            if(value == 'Ok'):
                return True
            elif(value == 'To be validated'):
                return None
            else:
                return False
