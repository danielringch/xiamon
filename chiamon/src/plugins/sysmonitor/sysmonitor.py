import psutil
from typing import DefaultDict, OrderedDict
from .resourceevaluator import Resourceevaluator
from ...core import Plugin, Alert, Config

class Sysmonitor(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('sysmonitor', 'name')
        super(Sysmonitor, self).__init__(name, outputs)
        self.print(f'Plugin sysmonitor; name: {name}')

        mute_interval, _ = config_data.get_value_or_default(24, 'alert_mute_interval')

        self.__evaluators = {}
        self.__alerts = {}
        self.__prefixes = {'load' : 'Load', 'ram' : 'RAM usage', 'swap' : 'Swap usage', 'temperature' : 'Temperature'}

        self.__add_resource(config_data.data, 'load', mute_interval)
        self.__add_resource(config_data.data, 'ram', mute_interval)
        self.__add_resource(config_data.data, 'swap', mute_interval)
        self.__add_resource(config_data.data, 'temperature', mute_interval)

        self.__temperature_source, _ = config_data.get_value_or_default(None, 'temperature', 'sensor')

        self.print(f'Monitored resources: {",".join(self.__evaluators.keys())}')

        scheduler.add_job(f'{name}-check' ,self.check, config_data.get_value_or_default('* * * * *', 'interval')[0])

    async def check(self):
        load = self.__check_resource('load', self.__get_load)
        ram = self.__check_resource('ram', self.__get_ram_usage)
        swap = self.__check_resource('swap', self.__get_swap_usage)
        temperature = self.__check_resource('temperature', self.__get_temperature)

        resource_strings = []

        if load is not None:
            resource_strings.append(f'{self.__prefixes["load"]}: {load:.2f}')
        if ram is not None:
            resource_strings.append(f'{self.__prefixes["ram"]}: {ram:.0f} %')
        if swap is not None:
            resource_strings.append(f'{self.__prefixes["swap"]}: {swap:.0f} %')
        if temperature is not None:
            resource_strings.append(f'{self.__prefixes["temperature"]}: {temperature:.1f} °C')

        if len(resource_strings) == 0:
            self.send(Plugin.Channel.debug, 'No resources to monitor.')
        else:
            self.send(Plugin.Channel.debug, ' | '.join(resource_strings))

    def __add_resource(self, config, key, mute_interval):
        if key not in config:
            return
        self.__evaluators[key] = Resourceevaluator(config[key])
        self.__alerts[key] = Alert(super(Sysmonitor, self), mute_interval)

    def __check_resource(self, key, getter):
        if key not in self.__evaluators:
            return None
        evaluator = self.__evaluators[key]
        value = getter()
        prefix = self.__prefixes[key]
        evaluator.update(value)
        if evaluator.treshold_exceeded:
            self.__alerts[key].send(f'{prefix} is high: {value:.2f} avg.')
        else:
            self.__alerts[key].reset(f'{prefix} is under treshold again.')
        return value


    def __get_ram_usage(self):
        ram = psutil.virtual_memory()
        return (ram.total - ram.available) / ram.total * 100.0

    def __get_swap_usage(self):
        return psutil.swap_memory().percent

    def __get_load(self):
        return psutil.getloadavg()[0]

    def __get_temperature(self):
        with open(self.__temperature_source, "r") as temp:
            return round(float(temp.read())/1000, 1)
