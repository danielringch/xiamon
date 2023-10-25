import ciso8601
from datetime import datetime
from .conversions import Conversions

class Hostdconsensusdata:
    def __init__(self, json):
        self.__synced = json['synced']
        self.__height = int(json['chainIndex']['height'])

    @property
    def synced(self):
        return self.__synced

    @property
    def height(self):
        return self.__height

class Hostdwalletdata:
    def __init__(self, json):
        self.__balance = Conversions.hasting_to_siacoin(int(json['confirmed']))
        self.__pending = Conversions.hasting_to_siacoin(int(json['unconfirmed']))
        self.__spendable = Conversions.hasting_to_siacoin(int(json['spendable']))

    @property
    def balance(self):
        return self.__balance

    @property
    def pending(self):
        return self.__pending

class Hostdmetricsdata:
    def __init__(self, json):
        self.__locked_collateral = Conversions.hasting_to_siacoin(int(json['contracts']['lockedCollateral']))
        self.__risked_collateral = Conversions.hasting_to_siacoin(int(json['contracts']['riskedCollateral']))
        self.__total_storage = int(json['storage']['totalSectors']) * 4194304
        self.__used_storage = int(json['storage']['physicalSectors']) * 4194304
        self.__ingress = int(json['data']['rhp2']['ingress']) + int(json['data']['rhp3']['ingress'])
        self.__egress = int(json['data']['rhp2']['egress']) + int(json['data']['rhp3']['egress'])
        self.__timestamp = ciso8601.parse_datetime(json['timestamp'])

    @property
    def locked_collateral(self):
        return self.__locked_collateral

    @property
    def risked_collateral(self):
        return self.__risked_collateral
    
    @property
    def total_storage(self):
        return self.__total_storage
    
    @property
    def used_storage(self):
        return self.__used_storage
    
    @property
    def ingress(self):
        return self.__ingress
    
    @property
    def egress(self):
        return self.__egress
    
    @property 
    def timestamp(self):
        return self.__timestamp
