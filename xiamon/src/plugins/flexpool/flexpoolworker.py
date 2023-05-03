import datetime

class FlexpoolWorker:
    def __init__(self, name, maximum_offline):
        self.__name = name
        self.__maximum_offline = maximum_offline * 3600
        self.__reset()
        
    @property
    def name(self):
        return self.__name
    
    @property
    def online(self):
        return self.__online
    
    @property
    def hashrate_reported(self):
        return self.__hashrate_reported
    
    @property
    def hashrate_average(self):
        return self.__hashrate_average
    
    @property
    def shares_valid(self):
        return self.__shares_valid
    
    @property
    def shares_stale(self):
        return self.__shares_stale
    
    @property
    def shares_invalid(self):
        return self.__shares_invalid

    def update(self, worker_status):
        self.__reset()
        for worker in worker_status:
            if worker['name'] != self.__name:
                continue

            last_seen = datetime.datetime.fromtimestamp(worker['lastSeen'])
            seconds_since_last_seen = (datetime.datetime.now() - last_seen).seconds

            self.__online = seconds_since_last_seen <= self.__maximum_offline
            self.__hashrate_reported = worker['reportedHashrate'] / 1000000000000.0
            self.__hashrate_average = worker['averageEffectiveHashrate'] / 1000000000000.0
            self.__shares_valid = worker['validShares']
            self.__shares_stale = worker['staleShares']
            self.__shares_invalid = worker['invalidShares']

    def __reset(self):
        self.__online = False
        self.__hashrate_reported = 0
        self.__hashrate_average = 0
        self.__shares_valid = 0
        self.__shares_stale = 0
        self.__shares_invalid = 0

