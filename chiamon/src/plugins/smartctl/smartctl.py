from datetime import datetime, timedelta
import os, subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config, Tablerenderer
from .smartctldb import Smartctldb
from .smartsnapshot import SmartSnapshot
from .attributeevaluator import AttributeEvaluator

class Smartctl(Plugin):

    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('smartctl', 'name')
        super(Smartctl, self).__init__(name, outputs)
        self.print(f'Plugin smartctl; name: {name}')
        
        self.__scheduler = scheduler
        self.__startup_job = f'{name}-startup'
        self.__check_job = f'{name}-check'
        self.__report_job = f'{name}-report'

        self.__aggregation = timedelta(hours=config_data.get_value_or_default(24, 'aggregation')[0])
        smartctl_directory = os.path.dirname(config_data.data['binary'])
        smartctl_file = os.path.basename(config_data.data['binary'])
        self.__smartctl_call = os.path.join(smartctl_directory, f'./{smartctl_file}')
        self.__db = Smartctldb(super(Smartctl, self), config_data.data['database'])

        self.__attributes_of_interest = set(int(x) for x in config_data.data['global_limits'].keys())

        self.__generic_evaluator = AttributeEvaluator(self.__aggregation, config_data.data['global_limits'], None)
        self.__custom_evaluators = {}
        if 'drives' in config_data.data:
            for drive, drive_config in config_data.data['drives'].items():
                self.__custom_evaluators[drive] = AttributeEvaluator(self.__aggregation, config_data.data['global_limits'], drive_config)
                self.__attributes_of_interest.union(int(x) for x in drive_config.keys())

        self.__aliases, _ = config_data.get_value_or_default({}, 'alias')
        self.__blacklist = set()
        for drive in config_data.get_value_or_default([], 'blacklist')[0]:
            self.__blacklist.add(drive)

        self.__mute_interval = self.__aggregation.total_seconds() // 3600
        self.__attribute_alerts = defaultdict(lambda: defaultdict(lambda: Alert(super(Smartctl, self), self.__mute_interval)))

        self.__scheduler.add_job(self.__startup_job ,self.startup, None)
        self.__scheduler.add_job(self.__check_job ,self.run, config_data.get_value_or_default('0 0 * * *', 'check_interval')[0])
        report_intervall, report_enabled = config_data.get_value_or_default(None, 'report_interval')
        if report_enabled:
            self.__scheduler.add_job(self.__report_job ,self.report, report_intervall)

    async def startup(self):
        message = []
        message.append(f'Monitored attributes: {", ".join(str(x) for x in self.__attributes_of_interest)}')
        drives =  self.__get_drives()
        for device in drives:
            snapshot = self.__get_smart_data(device)
            if not snapshot.success or snapshot.identifier in self.__blacklist:
                continue
            identifier = snapshot.identifier
            try:
                alias = f'({self.__aliases[identifier]})'
            except KeyError:
                alias = ''
            if identifier in self.__custom_evaluators:
                config = 'custom'
            else:
                config = 'default'
            message.append(f'Found drive {identifier} {alias} at {device} with {config} limits.')
        self.send(Plugin.Channel.debug, '\n'.join(message) if len(message) > 0 else 'No drives found.')     

    async def run(self):
        for device in self.__get_drives():
            snapshot = self.__get_smart_data(device)
            if not snapshot.success or snapshot.identifier in self.__blacklist:
                continue

            try:
                evaluator = self.__custom_evaluators[snapshot.identifier]
            except KeyError:
                evaluator = self.__generic_evaluator

            history = self.__db.get(snapshot.identifier, datetime.now() - self.__aggregation)
            self.__db.update(snapshot)

            evaluator_errors, evaluator_debugs = evaluator.check(snapshot, history)
            for error_key, error_message in evaluator_errors.items():
                try:
                    alias = self.__aliases[snapshot.identifier]
                except KeyError:
                    alias = snapshot.identifier
                alert = self.__attribute_alerts[snapshot.identifier][error_key]
                alert.send(f'{alias}: {error_message}')
            for debug_message in evaluator_debugs:
                self.send(Plugin.Channel.debug, f'{snapshot.identifier}: {debug_message}')

    async def report(self):
        last_execution = self.__scheduler.get_last_execution(self.__report_job)
        table = Tablerenderer(['Device', 'Alias'] + [str(x) for x in self.__attributes_of_interest])

        snapshots = [self.__get_smart_data(x) for x in self.__get_drives()]
        snapshots = [x for x in snapshots if (x.success and x.identifier not in self.__blacklist)]

        for snapshot in sorted(snapshots, key=lambda y: y.identifier):
            old_snapshot = self.__db.get(snapshot.identifier, last_execution)

            table.data['Device'].append(snapshot.identifier)
            try:
                alias = self.__aliases[snapshot.identifier]
            except KeyError:
                alias = ''
            table.data['Alias'].append(alias)

            for attribute, value in snapshot.attributes.items():
                try:
                    delta = value - old_snapshot.attributes[attribute]
                    cell = f'({delta:+}) {value}'
                except:
                    cell = str(value)
                table.data[str(attribute)].append(cell)

        self.send(Plugin.Channel.report, table.render())
        
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

    def __get_smart_data(self, device):
        output = subprocess.run([self.__smartctl_call,"-iA" , device], text=True, stdout=subprocess.PIPE)
        return SmartSnapshot.from_smartctl(output.stdout, self.__attributes_of_interest)
