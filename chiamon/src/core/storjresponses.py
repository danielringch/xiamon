from .conversions import Conversions

class Storjnodedata:
    def __init__(self, json):
        self.__connected = json['quicEnabled']
        self.__uptodate = json['upToDate']
        self.__traffic = int(json['bandwidth']['used'])
        self.__total_space = int(json['diskSpace']['available'])
        self.__used_space = int(json['diskSpace']['used'])
        self.__trash_space = int(json['diskSpace']['trash'])
        self.__overused_space = int(json['diskSpace']['overused'])
        self.__satellites = len(json['satellites'])
        self.__disqualified = 0
        self.__suspended = 0
        for satellite in json['satellites']:
            if satellite['disqualified'] is not None:
                self.__disqualified += 1
            if satellite['suspended'] is not None:
                self.__suspended += 1

    @property
    def connected(self):
        return self.__connected

    @property
    def uptodate(self):
        return self.__uptodate

    @property
    def traffic(self):
        return self.__traffic

    @property
    def total_space(self):
        return self.__total_space

    @property
    def used_space(self):
        return self.__used_space

    @property
    def trash_space(self):
        return self.__trash_space

    @property
    def overused_space(self):
        return self.__overused_space

    @property
    def satellites(self):
        return self.__satellites

    @property
    def disqualified(self):
        return self.__disqualified

    @property
    def suspended(self):
        return self.__suspended
