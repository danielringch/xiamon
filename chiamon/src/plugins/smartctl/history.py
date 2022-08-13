import os, yaml, ciso8601, copy, datetime
from .smartsnapshot import SmartSnapshot

class History:
    def __init__(self, dir, aggregation):
        self.__file = os.path.join(dir, 'smartdata.yaml')
        try:
            with open(self.__file, "r") as stream:
                self.__data = yaml.safe_load(stream)
        except FileNotFoundError:
            self.__data = {}
        self.__aggregation = datetime.timedelta(hours=aggregation)

    def update(self, snapshot):
        drive = snapshot.identifier
        attributes = snapshot.attributes
        drive_data = self.__data.setdefault(drive, {})
        if 'timestamp' not in drive_data or \
            ciso8601.parse_datetime(drive_data['timestamp']) + self.__aggregation < snapshot.timestamp:
            drive_data['timestamp'] = snapshot.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
            drive_data['attributes'] = copy.deepcopy(attributes)
            with open(self.__file, "w") as stream:
                yaml.safe_dump(self.__data, stream)

    def get(self, drive):
        if drive not in self.__data:
            return None
        drive_data = self.__data[drive]
        return SmartSnapshot.from_history(drive, drive_data['timestamp'], drive_data['attributes'])     
