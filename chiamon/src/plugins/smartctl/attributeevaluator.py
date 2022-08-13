
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

    def __init__(self, global_config, drive_config):
        self.__checkers = {}

        for attribute, check in global_config.items():
            self.__checkers[attribute] = AttributeEvaluator.checker_generators[check['evaluation']](check['value'])

        if drive_config is not None:
            for attribute, check in drive_config.items():
                self.__checkers[attribute] = AttributeEvaluator.checker_generators[check['evaluation']](check['value'])

    def check(self, snapshot, history):
        errors = {}

        for attribute, checker in self.__checkers.items():
            if attribute not in snapshot.attributes:
                continue

            value = snapshot.attributes[attribute]

            if history is not None and attribute in history.attributes:
                history_value = history.attributes[attribute]
            else:
                history_value = None

            passed, message = checker.check(value, history_value)

            if not passed:
                try:
                    readable_attribute = AttributeEvaluator.attribute_aliases[attribute]
                except KeyError:
                    readable_attribute = f'attribute {attribute}'

                errors[f'{attribute}-{checker.name}'] = f'{readable_attribute} {message}.'

        return errors


    class MaxCheck:
        def __init__(self, value):
            self.__value = value

        def check(self, attribute, _):
            if attribute > self.__value:
                return False, f'too high: {attribute}, max: {self.__value}'
            else:
                return True, ''
        
        @property
        def name(self):
            return 'max'

    class MinCheck:
        def __init__(self, value):
            self.__value = value

        def check(self, attribute, _):
            if attribute < self.__value:
                return False, f'too low: {attribute}, min: {self.__value}'
            else:
                return True, ''

        @property
        def name(self):
            return 'min'

    class DeltaMaxCheck:
        def __init__(self, value):
            self.__value = value

        def check(self, attribute, history):
            if history is None:
                return True, ''
            delta = attribute - history
            if delta > self.__value:
                return False, f'delta too high: {delta}, max: {self.__value}'
            else:
                return True, ''

        @property
        def name(self):
            return 'delta_max'

    class DeltaMinCheck:
        def __init__(self, value):
            self.__value = value

        def check(self, attribute, history):
            if history is None:
                return True, ''
            delta = attribute - history
            if delta < self.__value:
                return False, f'delta too low: {delta}, min: {self.__value}'
            else:
                return True, ''

        @property
        def name(self):
            return 'delta_min'
