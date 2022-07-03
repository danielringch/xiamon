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

    def traffic(self, unit):
        return Conversions.byte_to(unit, self.__traffic)

    def total_space(self, unit):
        return Conversions.byte_to(unit, self.__total_space)

    def used_space(self, unit):
        return Conversions.byte_to(unit, self.__used_space)

    def trash_space(self, unit):
        return Conversions.byte_to(unit, self.__trash_space)

    def overused_space(self, unit):
        return Conversions.byte_to(unit, self.__overused_space)

    @property
    def satellites(self):
        return self.__satellites

    @property
    def disqualified(self):
        return self.__disqualified

    @property
    def suspended(self):
        return self.__suspended
