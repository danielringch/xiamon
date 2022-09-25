import os, subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config, Tablerenderer
from .history import History
from .smartsnapshot import SmartSnapshot
from .attributeevaluator import AttributeEvaluator

class Smartctl(Plugin):

    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('smartctl', 'name')
        super(Smartctl, self).__init__(name, outputs)
        self.print(f'Plugin smartctl; name: {name}')

        self.__aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        smartctl_directory = os.path.dirname(config_data.data['binary'])
        smartctl_file = os.path.basename(config_data.data['binary'])
        self.__smartctl_call = os.path.join(smartctl_directory, f'./{smartctl_file}')
        self.__history = History(config_data.data['db'], self.__aggregation) 

        self.__attributes_of_interest = set(int(x) for x in config_data.data['global_limits'].keys())

        self.__generic_evaluator = AttributeEvaluator(config_data.data['global_limits'], None)
        self.__custom_evaluators = {}
        if 'drives' in config_data.data:
            for drive, drive_config in config_data.data['drives'].items():
                self.__custom_evaluators[drive] = AttributeEvaluator(config_data.data['global_limits'], drive_config)
                self.__attributes_of_interest.union(int(x) for x in drive_config.keys())

        self.__aliases, _ = config_data.get_value_or_default({}, 'alias')
        self.__blacklist = set()
        for drive in config_data.get_value_or_default([], 'blacklist')[0]:
            self.__blacklist.add(drive)

        self.__mute_interval = self.__aggregation
        self.__attribute_alerts = defaultdict(lambda: defaultdict(lambda: Alert(super(Smartctl, self), self.__mute_interval)))

        scheduler.add_job(f'{name}-startup' ,self.startup, None)
        scheduler.add_job(f'{name}-check' ,self.run, config_data.get_value_or_default('0 0 * * *', 'check_interval')[0])
        report_intervall, report_enabled = config_data.get_value_or_default(None, 'report_interval')
        if report_enabled:
            scheduler.add_job(f'{name}-report' ,self.report, report_intervall)

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

            self.__history.update(snapshot)
            history = self.__history.get(snapshot.identifier)

            for error_key, error_message in evaluator.check(snapshot, history).items():
                try:
                    alias = self.__aliases[snapshot.identifier]
                except KeyError:
                    alias = snapshot.identifier
                alert = self.__attribute_alerts[snapshot.identifier][error_key]
                alert.send(f'{alias}: {error_message}')

    async def report(self):
        table = Tablerenderer(['Device', 'Alias'] + [str(x) for x in self.__attributes_of_interest])

        snapshots = [self.__get_smart_data(x) for x in self.__get_drives()]
        snapshots = [x for x in snapshots if (x.success and x.identifier not in self.__blacklist)]

        for snapshot in sorted(snapshots, key=lambda y: y.identifier):
            table.data['Device'].append(snapshot.identifier)
            try:
                alias = self.__aliases[snapshot.identifier]
            except KeyError:
                alias = ''
            table.data['Alias'].append(alias)
            for attribute, value in snapshot.attributes.items():
                table.data[str(attribute)].append(value)

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
