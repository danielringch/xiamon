import asyncio
import croniter, datetime

class Scheduler:
    class __bundle:
        def __init__(self, name, func, interval):
            self.name = name
            self.func = func
            self.iter = croniter.croniter(interval, datetime.datetime.now())
            self.next = self.iter.get_next(datetime.datetime)


    def __init__(self):
        self.__jobs = {}

    def add_job(self, name, func, interval):
        job = Scheduler.__bundle(name, func, interval)
        self.__jobs[name] = job
        print(f'[scheduler] New job {job.name} added; next execution: {job.next}')

    async def manual(self, plugin):
        if plugin in self.__jobs:
            await self.__jobs[plugin].func()
        else:
            print(f'WARNING: job {plugin} not found.')

    async def run(self):
        time = datetime.datetime.now()
        tasks = []
        for job in self.__jobs.values():
            if job.next < time:
                job.next = job.iter.get_next(datetime.datetime)
                tasks.append(job.func())
        await asyncio.gather(*tasks)
