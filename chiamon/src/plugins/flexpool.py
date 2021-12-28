import yaml, aiohttp, datetime
from typing import DefaultDict
from ..core import Plugin, Alert, Alerts

__version__ = "0.1.1"

class Flexpool(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Flexpool, self).__init__('flexpool', outputs)
        self.print(f'Flexpool plugin {__version__}')
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)

        self.__address = config_data['address']
        self.__currency = config_data['currency']
        self.__check_workers = None if config_data['check_workers'] == 'all' else config_data['check_workers']

        self.__last_summary = datetime.datetime.now()
        self.__reported_space = DefaultDict(lambda: None)

        self.__connection_alerts = Alerts(super(Flexpool, self))
        self.__offline_alerts = Alerts(super(Flexpool, self))
        self.__connection_mute_intervall = config_data['connection_error_mute_intervall']
        self.__offline_mute_intervall = config_data['alert_mute_interval']

        scheduler.add_job('flexpool-summary' ,self.summary, config_data['summary_intervall'])
        scheduler.add_job('flexpool-check', self.check, config_data['check_intervall'])

    async def summary(self):
        since = self.__last_summary
        self.__last_summary = datetime.datetime.now
        async with aiohttp.ClientSession() as session:
            open_xch, open_money = await self.__get_balance(session)
            if open_xch is not None:
                message = (
                    f'Open balance: {open_xch} XCH ({open_money} {self.__currency})'
                )
                await self.send(Plugin.Channel.info, message)
            workers = await self.__get_worker_status(session)
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
            payments = await self.__get_payments(session, since)
            if payments is not None:
                for payment in payments:
                    message = (
                        f'Payment: {payment.value} XCH\n'
                        f'On {payment.timestamp} after {payment.duration}'
                    )
                    await self.send(Plugin.Channel.info, message)

    async def check(self):
        async with aiohttp.ClientSession() as session:
            workers = await self.__get_worker_status(session)
            if workers is None:
                return
            for worker in workers.values():
                if self.__ignore_worker(worker.name):
                    continue
                if not self.__offline_alerts.contains(worker.name):
                    self.__offline_alerts.add(worker.name,
                        Alert(super(Flexpool, self), self.__offline_mute_intervall))
                if not worker.online:
                    self.__offline_alerts.send(worker.name, f'Worker {worker.name} is offline.')
                    continue
                alert = self.__offline_alerts.get(worker.name)
                if alert.is_muted():
                    alert.unmute()
                    self.send(Plugin.Channel.info, f'Worker {worker.name} is online again.')
                last_space = self.__reported_space[worker.name]
                if last_space is not None and last_space > worker.reported_hashrate:
                    self.send(Plugin.Channel.alert,
                        f'Worker {worker.name}: Reported space space dropped (old: {last_space:.2f} TB new: {worker.reported_hashrate:.2f}')

    def __ignore_worker(self, name):
        if self.__check_workers is not None and name not in self.__check_workers:
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

    async def __get(self, session, cmd, params):
        data = {}
        try:
            async with session.get(f'https://api.flexpool.io/v2/{cmd}', params=params) as response:
                response.raise_for_status()
                data =  await response.json()
        except Exception as e:
            await self.__handle_connection_error(False, cmd, f'Command {cmd}: {str(e)}')
            return None
        if data['error'] is not None:
            await self.__handle_connection_error(False, cmd, f'Command {cmd}: {data["error"]}')
            return None
        await self.__handle_connection_error(True, cmd, f'Command {cmd} successful again.')
        return data['result']

    async def __handle_connection_error(self, success, cmd, message):
        if not self.__connection_alerts.contains(cmd):
            self.__connection_alerts.add(cmd, Alert(super(Flexpool, self), self.__connection_mute_intervall))
        alert = self.__connection_alerts.get(cmd)
        if success:
            await alert.send_unmute(message)
        else:
            await alert.send_unmute(message)

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

