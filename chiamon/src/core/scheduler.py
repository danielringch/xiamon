import croniter, datetime, asyncio, traceback
from collections import namedtuple
from .interface import Interface

Startupjob = namedtuple("Startupjob", "name func")

class Scheduler:
    class __bundle:
        def __init__(self, name, func, interval):
            self.name = name
            self.func = func
            self.iter = croniter.croniter(interval, datetime.datetime.now())
            self.next = self.iter.get_next(datetime.datetime)


    def __init__(self):
        self.__jobs = {}
        self.__startup_jobs = []
        self.__interfaces = []

    async def start(self, interfaces):
        self.__interfaces.extend(interfaces)
        for job in self.__jobs.values():
            await self.__print(Interface.Channel.debug, f'Job {job.name}; next execution: {job.next}')
        for startup_job in self.__startup_jobs:
            await self.__print(Interface.Channel.debug, f'Running startup job {startup_job.name}.')
            await self.__try_run(startup_job)
            
    def add_job(self, name, func, interval):
        if interval is None:
            self.__startup_jobs.append(Startupjob(name, func))
        else:
            self.__jobs[name] = Scheduler.__bundle(name, func, interval)

    async def manual(self, job):
        if job in self.__jobs:
            await self.__try_run(self.__jobs[job])
        else:
            await self.__print(Interface.Channel.error, f'Job {job} not found.')

    async def run(self):
        time = datetime.datetime.now()
        for job in self.__jobs.values():
            if job.next < time:
                await self.__try_run(job)
                job.next = job.iter.get_next(datetime.datetime)

    async def __try_run(self, job):
        try:
            await job.func()
        except Exception as e:
            trace = traceback.format_exc()
            message = f'Job {job.name} failed:\n{repr(e)}\n{trace}'
            await self.__print(Interface.Channel.error, message)

    async def __print(self, channel, message):
        tasks = []
        for interface in self.__interfaces:
            tasks.append(interface.send_message(channel, 'scheduler', message))
        await asyncio.gather(*tasks)
