import asyncio, aiohttp, datetime
from ...core import Plugin
from .flexpoolworker import FlexpoolWorker

class Flexpool(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Flexpool, self).__init__(config, outputs)

        self.__address = self.config.data['address']
        self.__currency = self.config.get('USD', 'currency')

        self.__workers = {}
        for worker_name, worker_settings in self.config.data['workers'].items():
            self.__workers[worker_name] = FlexpoolWorker(worker_name, float(worker_settings['maximum_offline_time']))

        self.__last_summary = datetime.datetime.now()

        self.__timeout = aiohttp.ClientTimeout(total=30)

        scheduler.add_job(f'{self.name}-summary' ,self.summary, self.config.get('0 * * * *', 'summary_interval'))
        scheduler.add_job(f'{self.name}-check', self.check, self.config.get('0 0 * * *', 'check_interval'))

    async def summary(self):
        now = datetime.datetime.now()
        async with aiohttp.ClientSession() as session:
            balance_task = self.__get_balance(session)
            workers_task = self.__update_workers(session)
            payments_task = self.__get_payments(session, self.__last_summary)
            balance, _, payments = await asyncio.gather(balance_task, workers_task, payments_task)
        open_xch = balance[0]
        open_money = balance[1]
        if open_xch is None or payments is None:
            self.msg.info('The following summary is incomplete, since one or more requests failed.')
        else:
            self.__last_summary = now
        if open_xch is not None:
            self.msg.info(f'Open balance: {open_xch} XCH ({open_money:.2f} {self.__currency})')
        for worker in self.__workers.values():
            self.msg.info(
                f'Worker {worker.name} ({"online" if worker.online else "offline"}):',
                f'Hashrate (reported | average): {worker.hashrate_reported:.2f} TB | {worker.hashrate_average:.2f} TB',
                f'Shares (valid | stale | invalid): {worker.shares_valid} | {worker.shares_stale_shares} | {worker.shares_invalid_shares}'
            )
        if payments is not None:
            if len(payments) == 0:
                self.msg.info('No new payments available')
            else:
                for payment in payments:
                    self.msg.info(
                        f'Payment: {payment.value} XCH',
                        f'On {payment.timestamp} after {payment.duration:.1f} d'
                    )

    async def check(self):
        async with aiohttp.ClientSession() as session:
            await self.__update_workers(session)
            for worker in self.__workers.values():
                if not worker.online:
                    self.alert(f'worker_{worker.name}', f'Worker {worker.name} is offline.')
                    continue
                self.reset_alert(f'worker_{worker.name}', f'Worker {worker.name} is online again.')

    async def __get_balance(self, session):
        params = {'coin': 'XCH', 'address': self.__address, 'countervalue': self.__currency }
        data = await self.__get(session, 'miner/balance', params)
        if data is None:
            return None, None
        return (data['balance'] / 1000000000000.0), data['balanceCountervalue']

    async def __update_workers(self, session):
        params = {'coin': 'XCH', 'address': self.__address}
        data = await self.__get(session, 'miner/workers', params)
        if data is None:
            return
        for worker in self.__workers.values():
            worker.update(data)

    async def __get_payments(self, session, since):
        params = {'coin': 'XCH', 'address': self.__address, 'page': 0}
        payments = []
        remaining_pages = None
        while True:
            data = await self.__get(session, 'miner/payments', params)
            if data is None:
                return None
            if len(data['data']) == 0:
                break;
            params['page'] += 1
            if remaining_pages is None:
                remaining_pages = data['totalPages']
            remaining_pages -= 1
            for payment_data in data['data']:
                payment = Flexpool.Payment(payment_data)
                if since is not None and payment.timestamp < since:
                    remaining_pages = 0
                    break
                payments.append(payment)
            if remaining_pages == 0:
                break
            
        return payments

    async def __get(self, session, cmd, params, retry=0):
        data = {}
        try:
            request = f'https://api.flexpool.io/v2/{cmd}'
            async with session.get(request, params=params, timeout=self.__timeout) as response:
                response.raise_for_status()
                data =  await response.json()
        except asyncio.TimeoutError as e_timeout:
            self.alert(f'cmd_{cmd}', f'Request {cmd}: timeout')
            return None
        except Exception as e:
            self.alert(f'cmd_{cmd}', f'Request {cmd}: {repr(e)}')
            return None
        if data['error'] is not None:
            self.alert(f'cmd_{cmd}', f'Request {cmd}: {data["error"]}')
            return None
        self.reset_alert(f'cmd_{cmd}', f'Request {cmd} successful again.')
        return data['result']

    class Payment:
        def __init__(self, json):
            self.timestamp = datetime.datetime.fromtimestamp(json['timestamp'])
            self.value = json['value'] / 1000000000000.0
            self.duration = float(json['duration']) / (3600.0 * 24.0)

