import datetime

class SpacefarmersWorker:
    def __init__(self, name, maximum_offline):
        self.__name = name
        self.__maximum_offline = datetime.timedelta(hours=maximum_offline)
        self.__latest_partial_timestamp = datetime.datetime.fromtimestamp(0)
        self.reset_statistics()
        
    @property
    def name(self):
        return self.__name
    
    @property
    def maximum_offline(self):
        return self.__maximum_offline
    
    @property
    def online(self):
        return self.__latest_partial_timestamp > (datetime.datetime.now() - self.__maximum_offline)
    
    @property
    def latest_partial_timestamp(self):
        return self.__latest_partial_timestamp

    @property
    def average_time(self):
        return self.__total_time / self.__valid_partials if self.__valid_partials > 0 else 0
    
    @property
    def partials_valid(self):
        return self.__valid_partials
    
    @property
    def partials_invalid(self):
        return self.__invalid_partials

    def update(self, partials, no_stats=False):
        for partial in partials:
            if not partial.harvester.startswith(self.__name):
                continue
            if partial.timestamp > self.__latest_partial_timestamp:
                self.__latest_partial_timestamp = partial.timestamp
            if no_stats:
                continue
            if partial.valid:
                self.__valid_partials += 1
                self.__total_time += partial.time
            else:
                self.__invalid_partials += 1

    def reset_statistics(self):
        self.__total_time = 0.0
        self.__valid_partials = 0
        self.__invalid_partials = 0

