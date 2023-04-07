import psutil, glob
from .resourceevaluator import Resourceevaluator
from ...core import Plugin, Alert, Config

class Sysmonitor(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Sysmonitor, self).__init__(config, outputs)

        self.__evaluators = {}
        self.__prefixes = {'load' : 'Load', 'ram' : 'RAM usage', 'swap' : 'Swap usage', 'temperature' : 'Temperature'}

        self.__add_resource(self.config.data, 'load')
        self.__add_resource(self.config.data, 'ram')
        self.__add_resource(self.config.data, 'swap')
        self.__add_resource(self.config.data, 'temperature')

        self.__temperature_source = self.config.get(None, 'temperature', 'sensor')

        self.print(f'Monitored resources: {",".join(self.__evaluators.keys())}')

        scheduler.add_job(f'{self.name}-check' ,self.check, self.config.get('* * * * *', 'interval'))

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
            self.msg.debug('No resources to monitor.')
        else:
            self.msg.debug(' | '.join(resource_strings))

    def __add_resource(self, config, key):
        if key not in config:
            return
        self.__evaluators[key] = Resourceevaluator(config[key])

    def __check_resource(self, key, getter):
        if key not in self.__evaluators:
            return None
        evaluator = self.__evaluators[key]
        value = getter()
        prefix = self.__prefixes[key]
        evaluator.update(value)
        if evaluator.treshold_exceeded:
            self.alert(key, f'{prefix} is high: {value:.2f} avg.')
        else:
            self.reset_alert(key, f'{prefix} is under treshold again.')
        return value

    def __get_ram_usage(self):
        ram = psutil.virtual_memory()
        return (ram.total - ram.available) / ram.total * 100.0

    def __get_swap_usage(self):
        return psutil.swap_memory().percent

    def __get_load(self):
        return psutil.getloadavg()[0]

    def __get_temperature(self):
        paths = glob.glob(self.__temperature_source)
        if len(paths) == 0:
            self.msg.error(f'Temperature file not found: {self.__temperature_source}')
            return 0
        with open(paths[0], "r") as temp:
            return round(float(temp.read())/1000, 1)
