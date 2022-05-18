import asyncio, aiohttp, datetime
from typing import DefaultDict
from ...core import Plugin, Alert, Config

class Flexpool(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('flexpool', 'name')
        super(Flexpool, self).__init__(name, outputs)
        self.print(f'Plugin flexpool; name: {name}')

        self.__address = config_data.data['address']
        self.__currency, _ = config_data.get_value_or_default('USD', 'currency')
        self.__worker_whitelist, _ = config_data.get_value_or_default(None, 'worker_whitelist')

        self.__last_summary = datetime.datetime.now()
        self.__reported_space = DefaultDict(lambda: None)

        self.__timeout = aiohttp.ClientTimeout(total=30)

        self.__connection_alerts = {}
        self.__connection_mute_interval, _ = config_data.get_value_or_default(24, 'connection_error_mute_interval')
        self.__connection_tolerance, _ = config_data.get_value_or_default(0, 'connection_error_tolerance')
        self.__connection_retry, _ = config_data.get_value_or_default(3, 'connection_retry')
        self.__offline_alerts = {}
        self.__offline_mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')
        self.__offline_tolerance, _ = config_data.get_value_or_default(0, 'alert_tolerance')

        scheduler.add_job(f'{name}-summary' ,self.summary, config_data.get_value_or_default('0 * * * *', 'summary_interval')[0])
        scheduler.add_job(f'{name}-check', self.check, config_data.get_value_or_default('0 0 * * *', 'check_interval')[0])

    async def summary(self):
        now = datetime.datetime.now()
        await self.send(Plugin.Channel.debug, f'Creating summary for address {self.__address}.')
        async with aiohttp.ClientSession() as session:
            balance_task = self.__get_balance(session)
            workers_task = self.__get_worker_status(session)
            payments_task = self.__get_payments(session, self.__last_summary)
            balance, workers, payments = await asyncio.gather(balance_task, workers_task, payments_task)
        open_xch = balance[0]
        open_money = balance[1]
        if open_xch is None or workers is None or payments is None:
            await self.send(Plugin.Channel.info, 'The following summary is incomplete, since one or more requests failed.')
        else:
            self.__last_summary = now
        if open_xch is not None:
            message = (
                f'Open balance: {open_xch} XCH ({open_money} {self.__currency})'
            )
            await self.send(Plugin.Channel.info, message)
        if workers is not None:
            for worker in workers.values():
                if self.__ignore_worker(worker.name):
                    continue
                message = (
                    f'Worker {worker.name} ({"online" if worker.online else "offline"}, last seen: {worker.last_seen}):\n'
                    f'Hashrate (reported | average): {worker.reported_hashrate:.2f} TB | {worker.average_hashrate:.2f} TB\n'
                    f'Shares (valid | stale | invalid): {worker.valid_shares} | {worker.stale_shares} | {worker.invalid_shares}'
                )
                await self.send(Plugin.Channel.info, message)
        if payments is not None:
            if len(payments) == 0:
                await self.send(Plugin.Channel.info, 'No new payments available')
            else:
                for payment in payments:
                    message = (
                        f'Payment: {payment.value} XCH\n'
                        f'On {payment.timestamp} after {payment.duration}'
                    )
                    await self.send(Plugin.Channel.info, message)    

    async def check(self):
        await self.send(Plugin.Channel.debug, f'Checking status for workers {",".join(self.__offline_alerts.keys())}.')
        async with aiohttp.ClientSession() as session:
            workers = await self.__get_worker_status(session)
            if workers is None:
                return
            for worker in workers.values():
                if self.__ignore_worker(worker.name):
                    continue
                if worker.name not in self.__offline_alerts:
                    self.__offline_alerts[worker.name] = Alert(super(Flexpool, self),
                        self.__offline_mute_interval, self.__offline_tolerance)
                alert = self.__offline_alerts[worker.name]
                if not worker.online:
                    await alert.send(f'Worker {worker.name} is offline.')
                    continue
                if alert.is_muted():
                    alert.reset(f'Worker {worker.name} is online again.')
                last_space = self.__reported_space[worker.name]
                if last_space is not None and last_space > worker.reported_hashrate:
                    await self.send(Plugin.Channel.alert,
                        f'Worker {worker.name}: Reported space space dropped (old: {last_space:.2f} TB new: {worker.reported_hashrate:.2f}')

    def __ignore_worker(self, name):
        if self.__worker_whitelist is not None and name not in self.__worker_whitelist:
            return True
        else:
            return False

    async def __get_balance(self, session):
        params = {'coin': 'XCH', 'address': self.__address, 'countervalue': self.__currency }
        data = await self.__get(session, 'miner/balance', params)
        if data is None:
            return None, None
        return (data['balance'] / 1000000000000.0), data['balanceCountervalue']

    async def __get_worker_status(self, session):
        params = {'coin': 'XCH', 'address': self.__address}
        data = await self.__get(session, 'miner/workers', params)
        if data is None:
            return None
        workers = []
        for worker in data:
            workers.append(Flexpool.WorkerStatus(worker))
        return {worker.name : worker for worker in workers}

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
            if retry < self.__connection_retry:
                await self.send(Plugin.Channel.debug, f'Retrying request {cmd} after timeout.')
                await asyncio.sleep(5)
                return await self.__get(session, cmd, params, retry + 1)
            else:
                await self.__handle_connection_error(False, cmd, f'Request {cmd}: timeout')
                return None
        except Exception as e:
            await self.__handle_connection_error(False, cmd, f'Request {cmd}: {repr(e)}')
            return None
        if data['error'] is not None:
            await self.__handle_connection_error(False, cmd, f'Request {cmd}: {data["error"]}')
            return None
        await self.__handle_connection_error(True, cmd, f'Request {cmd} successful again.')
        return data['result']

    async def __handle_connection_error(self, success, cmd, message):
        if cmd not in self.__connection_alerts:
            self.__connection_alerts[cmd] = Alert(super(Flexpool, self),
                self.__connection_mute_interval, self.__connection_tolerance)
        alert = self.__connection_alerts[cmd]
        if success:
            await alert.reset(message)
        else:
            await alert.send(message)

    class WorkerStatus:
        def __init__(self, json):
            self.name = json['name']
            self.online = json['isOnline']
            self.reported_hashrate = json['reportedHashrate'] / 1000000000000.0
            self.average_hashrate = json['averageEffectiveHashrate'] / 1000000000000.0
            self.valid_shares = json['validShares']
            self.stale_shares = json['staleShares']
            self.invalid_shares = json['invalidShares']
            self.last_seen = datetime.datetime.fromtimestamp(json['lastSeen'])

    class Payment:
        def __init__(self, json):
            self.timestamp = datetime.datetime.fromtimestamp(json['timestamp'])
            self.value = json['value'] / 1000000000000.0
            self.duration = datetime.timedelta(seconds=json['duration'])

