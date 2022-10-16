
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

    def __init__(self, aggregation, global_config, drive_config):
        self.__checkers = {}
        self.__aggregation = aggregation

        for attribute, check in global_config.items():
            self.__checkers[attribute] = AttributeEvaluator.checker_generators[check['evaluation']](check['value'])

        if drive_config is not None:
            for attribute, check in drive_config.items():
                self.__checkers[attribute] = AttributeEvaluator.checker_generators[check['evaluation']](check['value'])

    def check(self, snapshot, history):
        errors = {}
        debugs = []
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

            try:
                readable_attribute = AttributeEvaluator.attribute_aliases[attribute]
            except KeyError:
                readable_attribute = f'attribute {attribute}'

            if passed:
                debugs.append(f'{readable_attribute} {message}.')
            else:
                errors[f'{attribute}-{checker.name}'] = f'{readable_attribute} {message}.'

        return errors, debugs

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
                return True, 'test not executed.'
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
                return True, 'test not executed.'
            delta = value - old_value
            if delta < self.__limit:
                return False, f'delta too low: {delta}, min: {self.__limit}'
            else:
                return True, f'passed test; delta: {delta}, min delta: {self.__limit}'

        @property
        def name(self):
            return 'delta_min'
