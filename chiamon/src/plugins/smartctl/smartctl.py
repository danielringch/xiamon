import os, subprocess, re
from collections import defaultdict
from ...core import Plugin, Alert, Config
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

        self.__generic_evaluator = AttributeEvaluator(config_data.data['global_limits'], None)
        self.__custom_evaluators = {}
        if 'drives' in config_data.data:
            for drive, drive_config in config_data.data['drives'].items():
                self.__custom_evaluators[drive] = AttributeEvaluator(config_data.data['global_limits'], drive_config)

        self.__aliases, _ = config_data.get_value_or_default({}, 'alias')
        self.__blacklist = set()
        for drive in config_data.get_value_or_default([], 'blacklist')[0]:
            self.__blacklist.add(drive)

        self.__mute_interval = self.__aggregation
        self.__attribute_alerts = defaultdict(lambda: defaultdict(lambda: Alert(super(Smartctl, self), self.__mute_interval)))

        scheduler.add_job(f'{name}-startup' ,self.startup, None)
        scheduler.add_job(f'{name}-check' ,self.run, config_data.get_value_or_default('0 0 * * *', 'interval')[0])

    async def startup(self):
        message = []
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
        await self.send(Plugin.Channel.debug, '\n'.join(message) if len(message) > 0 else 'No drives found.')     

    async def run(self):
        drives =  self.__get_drives()

        for device in drives:
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
                await alert.send(f'{alias}: {error_message}')

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
        return SmartSnapshot.from_smartctl(output.stdout)
