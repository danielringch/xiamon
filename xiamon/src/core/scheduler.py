import croniter, traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable, Dict, List
from .interface import Channel, send_message

@dataclass
class StartupJob:
    name: str
    func: Callable[[], Awaitable[None]]

class Scheduler:
    class __bundle:
        def __init__(self, name: str, func: Callable[[], Awaitable[None]], interval: str):
            self.name = name
            self.cron = interval
            self.func = func
            self.iter = croniter.croniter(interval, datetime.now(), ret_type=datetime)
            self.next = self.iter.get_next()

    def __init__(self):
        self.__jobs: Dict[str, Scheduler.__bundle] = {}
        self.__startup_jobs: List[StartupJob] = []

    async def start(self):
        for job in self.__jobs.values():
            self.__print(Channel.DEBUG, f'Job {job.name}; next execution: {job.next}')
        for startup_job in self.__startup_jobs:
            self.__print(Channel.DEBUG, f'Running startup job {startup_job.name}.')
            await self.__try_run(startup_job)
            
    def add_job(self, name: str, func: Callable[[], Awaitable[None]], interval: str | None):
        if interval:
            self.__jobs[name] = Scheduler.__bundle(name, func, interval)

    def add_startup_job(self, name: str, func: Callable[[], Awaitable[None]]):
        self.__startup_jobs.append(StartupJob(name, func))

    async def manual(self, job: str):
        if (func := self.__jobs.get(job)):
            await self.__try_run(func)
        else:
            self.__print(Channel.ERROR, f'Job {job} not found.')

    def get_last_execution(self, job: str):
        bundle = self.__jobs[job]
        iter = croniter.croniter(bundle.cron, bundle.next, ret_type=datetime)
        return iter.get_prev()

    def get_current_interval(self, job: str):
        bundle = self.__jobs[job]
        now = datetime.now()
        next_iter = croniter.croniter(bundle.cron, now, ret_type=datetime)
        prev_iter = croniter.croniter(bundle.cron, now, ret_type=datetime)
        return next_iter.get_next() - prev_iter.get_prev()
        
    async def run(self):
        time = datetime.now()
        for job in self.__jobs.values():
            if (job.next - time).total_seconds() < 0:
                await self.__try_run(job)
                job.next = job.iter.get_next()

        wait_seconds = min((max(0, (x.next - time).total_seconds()) for x in self.__jobs.values()), default=3600)
        return round(wait_seconds) + 1

    async def __try_run(self, job: 'Scheduler.__bundle'):
        try:
            await job.func()
        except Exception as e:
            trace = traceback.format_exc()
            message = f'Job {job.name} failed:\n{repr(e)}\n{trace}'
            self.__print(Channel.ERROR, message)

    def __print(self, channel: Channel, message: str):
        send_message(channel, message, 'scheduler')
