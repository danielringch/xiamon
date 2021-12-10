import asyncio
import croniter, datetime

class Scheduler:
    class __bundle:
        def __init__(self, name, func, intervall):
            self.name = name
            self.func = func
            self.iter = croniter.croniter(intervall, datetime.datetime.now())
            self.next = self.iter.get_next(datetime.datetime)


    def __init__(self):
        self.__jobs = []

    def add_job(self, name, func, intervall):
        job = Scheduler.__bundle(name, func, intervall)
        self.__jobs.append(job)
        print(f'[scheduler] New job {job.name} added; next execution: {job.next}')

    async def force_all(self):
        tasks = []
        for job in self.__jobs:
            tasks.append(job.func())
        await asyncio.gather(*tasks)

    async def run(self):
        time = datetime.datetime.now()
        tasks = []
        for job in self.__jobs:
            if job.next < time:
                job.next = job.iter.get_next(datetime.datetime)
                tasks.append(job.func())
        await asyncio.gather(*tasks)
