from ...core import Plugin, Alert

class AttributeEvaluator:
    attribute_aliases = {
        4: 'Start Stop Count',
        5: 'Reallocated Sectors Count',
        190: 'Airflow Temperature Celsius',
        193: 'Load Cycle Count',
        194: 'Temperature Celsius',
        197: 'Current Pending Sector Count'
    }

    checker_generators = {
        'max': lambda x: AttributeEvaluator.MaxCheck(x),
        'min': lambda x: AttributeEvaluator.MinCheck(x),
        'delta_max': lambda x: AttributeEvaluator.DeltaMaxCheck(x),
        'delta_min': lambda x: AttributeEvaluator.DeltaMaxCheck(x),
    }

    def __init__(self, plugin, aggregation, config, drive):
        self.__plugin = plugin
        self.name = config.get(drive, 'drives', drive, 'alias')
        self.config_type = 'default'
        self.__checkers = {}
        self.__aggregation = aggregation
        self.__alerts = {}

        global_config = config.get(None, 'limits')
        if global_config is not None:
            for attribute, check in global_config.items():
                self.__checkers[attribute] = self.checker_generators[check['evaluation']](check['value'])

        drive_config = config.get(None, 'drives', drive, 'limits')
        if drive_config is not None:
            self.config_type = 'custom'
            for attribute, check in drive_config.items():
                self.__checkers[attribute] = self.checker_generators[check['evaluation']](check['value'])

        for attribute in self.__checkers.keys():
            self.__alerts[attribute] = Alert(self.__plugin, self.__aggregation)

    def check(self, snapshot, history):
        if history is not None:
            delta = snapshot.timestamp - history.timestamp

        for attribute, checker in self.__checkers.items():
            try:
                value = snapshot.attributes[attribute]
            except KeyError:
                continue

            if history is not None:
                try:
                    history_value = self.__scale_value(value, history.attributes[attribute], delta, self.__aggregation) 
                except KeyError:
                    history_value = None
            else:
                history_value = None

            passed, message = checker.check(value, history_value)

            readable_attribute = self.attribute_aliases.get(attribute, f'attribute {attribute}')
            message = f'{self.name}: {readable_attribute} {message}.'
            self.__plugin.msg.debug(message)
            if not passed:
                self.__alerts[attribute].send(message)

    def __scale_value(self, value, old_value, time_delta, expected_time_delta):
        factor = expected_time_delta / time_delta
        delta = value - old_value
        scaled_delta = delta * factor
        return round(value - scaled_delta)

    class MaxCheck:
        def __init__(self, limit):
            self.__limit = limit

        def check(self, value, _):
            if value > self.__limit:
                return False, f'too high; {value}, max: {self.__limit}'
            else:
                return True, f'passed test; {value}, max: {self.__limit}'
        
        @property
        def name(self):
            return 'max'

    class MinCheck:
        def __init__(self, limit):
            self.__limit = limit

        def check(self, value, _):
            if value < self.__limit:
                return False, f'too low; {value}, min: {self.__limit}'
            else:
                return True, f'passed test; {value}, min: {self.__limit}'

        @property
        def name(self):
            return 'min'

    class DeltaMaxCheck:
        def __init__(self, limit):
            self.__limit = limit

        def check(self, value, old_value):
            if old_value is None:
                return True, 'test not executed'
            delta = value - old_value
            if delta > self.__limit:
                return False, f'delta too high; {delta}, max: {self.__limit}'
            else:
                return True, f'passed test; delta: {delta}, max delta: {self.__limit}'

        @property
        def name(self):
            return 'delta_max'

    class DeltaMinCheck:
        def __init__(self, limit):
            self.__limit = limit

        def check(self, value, old_value):
            if old_value is None:
                return True, 'test not executed'
            delta = value - old_value
            if delta < self.__limit:
                return False, f'delta too low: {delta}, min: {self.__limit}'
            else:
                return True, f'passed test; delta: {delta}, min delta: {self.__limit}'

        @property
        def name(self):
            return 'delta_min'
