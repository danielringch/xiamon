from datetime import datetime, timedelta
import os, subprocess, re
from ...core import Plugin, Config, Tablerenderer
from .smartctldb import Smartctldb
from .smartsnapshot import SmartSnapshot
from .attributeevaluator import AttributeEvaluator

class Smartctl(Plugin):
    def __init__(self, config, scheduler, outputs):
        self.__config = Config(config)
        name = self.__config.get('smartctl', 'name')
        super(Smartctl, self).__init__(name, outputs)
        self.print(f'Plugin smartctl; name: {name}')
        
        self.__scheduler = scheduler
        self.__startup_job = f'{name}-startup'
        self.__cleanup_job = f'{name}-cleanup'
        self.__check_job = f'{name}-check'
        self.__report_job = f'{name}-report'

        self.__smartctl_call = os.path.join(
            os.path.dirname(self.__config.data["binary"]),
            f'./{os.path.basename(self.__config.data["binary"])}')

        self.__db = Smartctldb(super(Smartctl, self), self.__config.data['database'])
        self.__aggregation = timedelta(hours=self.__config.get(24, 'aggregation'))
        self.__expiration = timedelta(days=self.__config.get(180, 'expiration'))

        self.__attributes_of_interest = set()
        self.__attributes_of_interest.update(int(x) for x in self.__config.get({}, 'limits').keys())
        for drive in self.__config.get({}, 'drives').values():
            self.__attributes_of_interest.update(drive.get('limits', {}).keys())

        self.__drives = {}

        self.__blacklist = set(self.__config.get([], 'blacklist'))

        self.__scheduler.add_startup_job(self.__startup_job, self.startup)
        self.__scheduler.add_job(self.__cleanup_job, self.cleanup, '0 0 * * *')
        self.__scheduler.add_job(self.__check_job, self.run, self.__config.get('0 * * * *', 'check_interval'))
        self.__scheduler.add_job(self.__report_job, self.report, self.__config.get(None, 'report_interval'))

    async def startup(self):
        self.msg.debug(f'Monitored attributes: {", ".join(str(x) for x in self.__attributes_of_interest)}')
        drives = self.__get_drives()
        for device in drives:
            identifier = self.__get_identifier(device)
            if identifier in self.__blacklist:
                self.msg.debug(f'Ignored blacklisted drive {identifier}.')
                continue
            snapshot = self.__get_smart_data(device, identifier)
            if not snapshot.success:
                self.msg.debug(f'Drive {identifier} has no SMART support.')
                self.__blacklist.add(identifier)
                continue
            self.__add_drive(snapshot.identifier, device) 

    async def cleanup(self):
        limit = datetime.now() - self.__expiration
        self.__db.delete_older_than(limit)

    async def run(self):
        with self.message_aggregator():
            for snapshot, evaluator in self.__get_snapshots():
                history = self.__db.get(snapshot.identifier, datetime.now() - self.__aggregation)
                self.__db.update(snapshot)
                evaluator.check(snapshot, history)

    async def report(self):
        last_execution = self.__scheduler.get_last_execution(self.__report_job)
        table = Tablerenderer(['Device', 'Alias'] + [str(x) for x in sorted(self.__attributes_of_interest)])

        for snapshot, evaluator in sorted(self.__get_snapshots(), key=lambda y: y[1].name):
            old_snapshot = self.__db.get(snapshot.identifier, last_execution)

            table.data['Device'].append(snapshot.identifier)
            table.data['Alias'].append(evaluator.name if evaluator.name != snapshot.identifier else '')

            for attribute, value in snapshot.attributes.items():
                try:
                    delta = value - old_snapshot.attributes[attribute]
                    cell = f'({delta:+}) {value}'
                except:
                    cell = str(value)
                table.data[str(attribute)].append(cell)

        self.msg.report(table.render())
        
    def __get_drives(self):
        lsblk_output = subprocess.run(["lsblk","-o" , "KNAME"], text=True, stdout=subprocess.PIPE)
        drive_pattern = re.compile("sd\\D+$")
        drives = set()
        for line in lsblk_output.stdout.splitlines():
            device_match = drive_pattern.search(line)
            if not device_match:
                continue
            device = f'/dev/{line}'
            drives.add(device)
        return drives

    def __add_drive(self, identifier, device):
        evaluator = self.__drives.get(identifier, None)
        if evaluator is None:
            evaluator = AttributeEvaluator(super(Smartctl, self), self.__aggregation, self.__config, identifier)
            self.__drives[identifier] = evaluator
            self.msg.debug(f'Found drive {evaluator.name} at {device} with {evaluator.config_type} limits.')
        return evaluator

    def __get_snapshots(self):
        result = []
        for device in self.__get_drives():
            identifier = self.__get_identifier(device)
            if identifier in self.__blacklist:
                continue
            snapshot = self.__get_smart_data(device, identifier)
            if not snapshot.success:
                continue

            result.append((snapshot, self.__add_drive(snapshot.identifier, device)))
        return result

    def __get_identifier(self, device):
        output = subprocess.run(["lsblk", device,"-o", "MODEL,SERIAL"], text=True, stdout=subprocess.PIPE)
        lines = output.stdout.splitlines()
        if len(lines) < 2:
            return None
        return lines[1].replace(" ", "_")


    def __get_smart_data(self, device, identifier):
        output = subprocess.run([self.__smartctl_call,"-A" , device], text=True, stdout=subprocess.PIPE)
        return SmartSnapshot.from_smartctl(
            identifier, 
            output.stdout, 
            self.__attributes_of_interest)
