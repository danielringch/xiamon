from .conversions import Conversions

class Storjnodedata:
    def __init__(self, json):
        self.__quic = (json['quicStatus'] == "OK")
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
    def quic(self):
        return self.__quic

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

class Storjpayoutdata:
    class Month:
        def __init__(self, json):
            self.__storage = int(json['diskSpace'])
            self.__egress_bandwidth = int(json['egressBandwidth'])
            self.__repair_audit_bandwidth = int(json['egressRepairAudit'])
            self.__storage_reward = float(json['diskSpacePayout']) / 100.0
            self.__egress_reward = float(json['egressBandwidthPayout']) / 100.0
            self.__repair_audit_reward = float(json['egressRepairAuditPayout']) / 100.0
            self.__held_reward = float(json['held']) / 100.0

        @property
        def storage(self):
            return self.__storage

        @property
        def egress_bandwidth(self):
            return self.__egress_bandwidth

        @property
        def repair_audit_bandwidth(self):
            return self.__repair_audit_bandwidth

        @property
        def storage_reward(self):
            return self.__storage_reward

        @property
        def egress_reward(self):
            return self.__egress_reward

        @property
        def repair_audit_reward(self):
            return self.__repair_audit_reward

        @property
        def held_reward(self):
            return self.__held_reward

    def __init__(self, json):
        self.__current = self.Month(json['currentMonth'])
        self.__last = self.Month(json['previousMonth'])

    @property
    def current_month(self):
        return self.__current

    @property
    def last_month(self):
        return self.__last