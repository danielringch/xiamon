from datetime import datetime, timedelta
import os, subprocess, re
from ...core import Plugin, Tablerenderer
from .smartctldb import Smartctldb
from .smartsnapshot import SmartSnapshot
from .attributeevaluator import AttributeEvaluator

class Smartctl(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Smartctl, self).__init__(config, outputs)
        
        self.__scheduler = scheduler
        self.__startup_job = f'{self.name}-startup'
        self.__cleanup_job = f'{self.name}-cleanup'
        self.__check_job = f'{self.name}-check'
        self.__report_job = f'{self.name}-report'

        binary_path = self.config.get('/usr/sbin/smartctl', 'binary')
        self.__smartctl_call = os.path.join(os.path.dirname(binary_path),f'./{os.path.basename(binary_path)}')
        self.__use_sudo = binary_path.startswith('/usr/sbin')

        self.__db = Smartctldb(super(Smartctl, self), self.config.data['database'])
        self.__aggregation = timedelta(hours=self.config.get(24, 'aggregation'))
        self.__expiration = timedelta(days=self.config.get(180, 'expiration'))

        self.__attributes_of_interest = set()
        self.__attributes_of_interest.update(int(x) for x in self.config.get({}, 'limits').keys())
        for drive in self.config.get({}, 'drives').values():
            self.__attributes_of_interest.update(drive.get('limits', {}).keys())

        self.__drives = {}

        self.__blacklist = set(self.config.get([], 'blacklist'))

        self.__scheduler.add_startup_job(self.__startup_job, self.startup)
        self.__scheduler.add_job(self.__cleanup_job, self.cleanup, '0 0 * * *')
        self.__scheduler.add_job(self.__check_job, self.run, self.config.get('0 * * * *', 'check_interval'))
        self.__scheduler.add_job(self.__report_job, self.report, self.config.get(None, 'report_interval'))

    async def startup(self):
        self.msg.debug(f'Monitored attributes: {", ".join(str(x) for x in self.__attributes_of_interest)}')
        drives = self.__get_drives()
        for device in drives:
            identifier = self.__get_identifier(device)
            if identifier is None:
                self.msg.debug(f'Drive {device} has no SMART support.')
                continue
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
        attribute_columns = sorted(self.__attributes_of_interest)
        table = Tablerenderer(['Device', 'Alias'] + [str(x) for x in attribute_columns] )

        for snapshot, evaluator in sorted(self.__get_snapshots(), key=lambda y: y[1].name):
            old_snapshot = self.__db.get(snapshot.identifier, last_execution)

            row = []
            row.append(snapshot.identifier)
            row.append(evaluator.name if evaluator.name != snapshot.identifier else '')

            for attribute in attribute_columns:
                if attribute in snapshot.attributes:
                    value = snapshot.attributes[attribute]
                    try:
                        delta = value - old_snapshot.attributes[attribute]
                        row.append(f'({delta:+}) {value}')
                    except:
                        row.append(str(value))
                else:
                    row.append('')
            table.add_row(row)

        self.msg.verbose(table.render())
        
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
            evaluator = AttributeEvaluator(super(Smartctl, self), self.__aggregation, self.config, identifier)
            self.__drives[identifier] = evaluator
            self.msg.debug(f'Found drive {evaluator.name} at {device} with {evaluator.config_type} limits.')
        return evaluator

    def __get_snapshots(self):
        result = []
        for device in self.__get_drives():
            identifier = self.__get_identifier(device)
            if identifier is None or identifier in self.__blacklist:
                continue
            snapshot = self.__get_smart_data(device, identifier)
            if not snapshot.success:
                continue

            result.append((snapshot, self.__add_drive(snapshot.identifier, device)))
        return result

    def __get_identifier(self, device):
        output = self.__call_smartctl("-i", device)
        model = None
        serial = None
        for line in output.stdout.splitlines():
            if line.startswith('Device Model:     '):
                model = line[18:]
            elif line.startswith('Serial Number:    '):
                serial = line[18:]
                break
        if model is None or serial is None:
            return None
        return f'{model.replace(" ", "_")}_{serial.replace(" ", "_")}'

    def __get_smart_data(self, device, identifier):
        output = self.__call_smartctl("-A", device)
        return SmartSnapshot.from_smartctl(
            identifier, 
            output.stdout, 
            self.__attributes_of_interest)
    
    def __call_smartctl(self, flag, device):
        if self.__use_sudo:
            call = ['sudo', self.__smartctl_call, flag, device]
        else:
            call = [self.__smartctl_call, flag, device]

        return subprocess.run(call, text=True, stdout=subprocess.PIPE)
