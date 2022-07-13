import re

class SmartctlParser:
    def __init__(self, data):
        self.__identifier = None
        self.__attributes = {}
        self.__model = None
        self.__serial = None

        header_found = False
        header_regex = re.compile('^ID#.*RAW_VALUE$')
        no_whitespace_regex = re.compile('\\S+')
        id_index = 0
        value_index = None
        for line in data.splitlines():
            if not header_found:
                if line.startswith('Device Model:     '):
                    self.__model = line[18:]
                elif line.startswith('Serial Number:    '):
                    self.__serial = line[18:]
                elif header_regex.search(line):
                    columns = no_whitespace_regex.findall(line)
                    value_index = len(columns) - 1
                    header_found = True
            elif line:
                columns = no_whitespace_regex.findall(line)
                id = int(columns[id_index])
                try:
                    value = int(columns[value_index])
                    self.__attributes[id] = value
                except ValueError:
                    pass
            else:
                break
        self.__success = self.__model is not None and self.__serial is not None
        self.__identifier = f'{self.__model}-{self.__serial}'.replace(' ', '-') if self.__success else None

    @property
    def identifier(self):
        return self.__identifier

    @property
    def success(self):
        return self.__success

    @property
    def attributes(self):
        return self.__attributes
