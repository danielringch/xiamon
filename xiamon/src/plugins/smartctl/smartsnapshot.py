import re, datetime, copy

class SmartSnapshot:
    def __init__(self):
        self.__identifier = None
        self.__timestamp = datetime.datetime.now()
        self.__attributes = {}
        self.__success = False

    @classmethod
    def from_smartctl(cls, identifier, smartctl_out, attributes_of_interest):
        instance = cls()

        header_found = False
        header_regex = re.compile('^ID#.*RAW_VALUE$')
        no_whitespace_regex = re.compile('\\S+')
        id_index = 0
        value_index = None
        for line in smartctl_out.splitlines():
            if not header_found:
                if header_regex.search(line):
                    columns = no_whitespace_regex.findall(line)
                    value_index = len(columns) - 1
                    header_found = True
            elif line:
                columns = no_whitespace_regex.findall(line)
                id = int(columns[id_index])
                if id not in attributes_of_interest:
                    continue
                try:
                    value = int(columns[value_index])
                    instance.__attributes[id] = value
                except ValueError:
                    pass
            else:
                break
        instance.__success = identifier is not None and len(instance.attributes) > 0
        instance.__identifier = identifier

        return instance

    @classmethod
    def from_history(cls, identifier, timestamp, attributes):
        instance = cls()
        instance.__identifier = identifier
        instance.__timestamp = timestamp
        instance.__attributes = copy.deepcopy(attributes)
        instance.__success = True
        return instance

    @property
    def identifier(self):
        return self.__identifier

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def success(self):
        return self.__success

    @property
    def attributes(self):
        return self.__attributes
