import os, yaml, ciso8601, copy, datetime

class History:
    def __init__(self, dir, aggregation):
        self.__file = os.path.join(dir, 'smartdata.yaml')
        try:
            with open(self.__file, "r") as stream:
                self.__data = yaml.safe_load(stream)
        except FileNotFoundError:
            self.__data = {}
        self.__aggregation = datetime.timedelta(hours=aggregation)

    def update(self, parser):
        drive = parser.identifier
        attributes = parser.attributes
        drive_data = self.__data.setdefault(drive, {})
        if 'timestamp' not in drive_data or \
            ciso8601.parse_datetime(drive_data['timestamp']) + self.__aggregation < datetime.datetime.now():
            drive_data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            drive_data['attributes'] = copy.deepcopy(attributes)
            with open(self.__file, "w") as stream:
                yaml.safe_dump(self.__data, stream)

    def get_diff(self, drive, id, current_value):
        if drive not in self.__data:
            return None, None
        drive_data = self.__data[drive]
        drive_attributes = drive_data['attributes']
        if id not in drive_attributes:
            return None, None
        value = drive_attributes[id]
        time_diff = datetime.datetime.now() - ciso8601.parse_datetime(drive_data['timestamp'])
        return (current_value - value), time_diff        
