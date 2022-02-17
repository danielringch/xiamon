import croniter, datetime, asyncio
from .interface import Interface

class Scheduler:
    class __bundle:
        def __init__(self, name, func, interval):
            self.name = name
            self.func = func
            self.iter = croniter.croniter(interval, datetime.datetime.now())
            self.next = self.iter.get_next(datetime.datetime)


    def __init__(self):
        self.__jobs = {}
        self.__interfaces = []

    async def start(self, interfaces):
        self.__interfaces.extend(interfaces)
        for job in self.__jobs.values():
            await self.__print(Interface.Channel.debug, f'Job {job.name}; next executtion: {job.next}')

    def add_job(self, name, func, interval):
        self.__jobs[name] = Scheduler.__bundle(name, func, interval)

    async def manual(self, plugin):
        if plugin in self.__jobs:
            await self.__try_run(self.__jobs[plugin])
        else:
            await self.__print(Interface.Channel.error, f'Job {plugin} not found.')

    async def run(self):
        time = datetime.datetime.now()
        tasks = []
        for job in self.__jobs.values():
            if job.next < time:
                job.next = job.iter.get_next(datetime.datetime)
                tasks.append(self.__try_run(job))
        await asyncio.gather(*tasks)

    async def __try_run(self, job):
        try:
            await job.func()
        except Exception as e:
            await self.__print(Interface.Channel.error, f'Job {job.name} failed with:\n{repr(e)}')

    async def __print(self, channel, message):
        tasks = []
        for interface in self.__interfaces:
            tasks.append(interface.send_message(channel, 'scheduler', message))
        await asyncio.gather(*tasks)
