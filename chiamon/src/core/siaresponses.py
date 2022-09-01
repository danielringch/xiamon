from .conversions import Conversions

class Siaconsensusdata:
    def __init__(self, json):
        self.__synced = json['synced']
        self.__height = int(json['height'])

    @property
    def synced(self):
        return self.__synced

    @property
    def height(self):
        return self.__height

class Siawalletdata:
    def __init__(self, json):
        self.__unlocked = json['unlocked']
        self.__balance = Conversions.hasting_to_siacoin(int(json['confirmedsiacoinbalance']))
        incoming = int(json['unconfirmedincomingsiacoins'])
        outgoing = int(json['unconfirmedoutgoingsiacoins'])
        self.__pending = Conversions.hasting_to_siacoin(incoming - outgoing)

    @property
    def unlocked(self):
        return self.__unlocked

    @property
    def balance(self):
        return self.__balance

    @property
    def pending(self):
        return self.__pending

class Siahostdata:
    def __init__(self, json):
        self.__accepting = json['externalsettings']['acceptingcontracts']
        self.__address = json['externalsettings']['netaddress']
        self.__contractprice = Conversions.hasting_to_siacoin(int(json['internalsettings']['mincontractprice']))
        self.__storageprice = Conversions.hastingsbyteblock_to_siacointerabytemonth(int(json['internalsettings']['minstorageprice']))
        self.__collateral = Conversions.hastingsbyteblock_to_siacointerabytemonth(int(json['internalsettings']['collateral']))
        self.__uploadprice = Conversions.hastingbyte_to_siacointerabyte(int(json['internalsettings']['minuploadbandwidthprice']))
        self.__downloadprice = Conversions.hastingbyte_to_siacointerabyte(int(json['internalsettings']['mindownloadbandwidthprice']))
        self.__sectorprice = Conversions.hasting_to_siacoin(int(json['internalsettings']['minsectoraccessprice']))
        self.__rpcprice = Conversions.hasting_to_siacoin(int(json['internalsettings']['minbaserpcprice']))
        self.__contracts = json['financialmetrics']['contractcount']
        self.__collateralbudget = Conversions.hasting_to_siacoin(int(json['internalsettings']['collateralbudget']))
        self.__storagerevenue = Conversions.hasting_to_siacoin(int(json['financialmetrics']['storagerevenue']))
        self.__downloadrevenue = Conversions.hasting_to_siacoin(int(json['financialmetrics']['downloadbandwidthrevenue']))
        self.__uploadrevenue = Conversions.hasting_to_siacoin(int(json['financialmetrics']['uploadbandwidthrevenue']))
        self.__statusok = json['connectabilitystatus'] == 'connectable' and json['workingstatus'] == 'working'

    @property
    def accepting(self):
        return self.__accepting

    @property
    def address(self):
        return self.__address

    @property
    def contractprice(self):
        return self.__contractprice

    @property
    def storageprice(self):
        return self.__storageprice

    @property
    def collateral(self):
        return self.__collateral

    @property
    def uploadprice(self):
        return self.__uploadprice

    @property
    def downloadprice(self):
        return self.__downloadprice

    @property
    def sectorprice(self):
        return self.__sectorprice

    @property
    def rpcprice(self):
        return self.__rpcprice

    @property
    def contracts(self):
        return self.__contracts

    @property
    def collateralbudget(self):
        return self.__collateralbudget

    @property
    def storagerevenue(self):
        return self.__storagerevenue

    @property
    def downloadrevenue(self):
        return self.__downloadrevenue

    @property
    def uploadrevenue(self):
        return self.__uploadrevenue

    @property
    def statusok(self):
        return self.__statusok

class Siastoragedata:
    def __init__(self, json):
        self.__folders = []
        self.__total = 0
        self.__remaining = 0
        self.__used = 0
        for json_folder in json['folders']:
            folder = Siastoragedata.Folder(json_folder)
            self.__total += folder.total_space
            self.__remaining += folder.free_space
            self.__used += folder.used_space
            self.__folders.append(folder)

    @property
    def folders(self):
        return self.__folders

    @property
    def total_space(self):
        return self.__total

    @property
    def free_space(self):
        return self.__remaining
        
    @property
    def used_space(self):
        return self.__used

    class Folder:
        def __init__(self, json):
            self.__path = json['path']
            self.__total = json['capacity']
            self.__remaining = json['capacityremaining']
            self.__used = self.__total - self.__remaining

        @property
        def path(self):
            return self.__path

        @property
        def total_space(self):
            return self.__total

        @property
        def free_space(self):
            return self.__remaining
        
        @property
        def used_space(self):
            return self.__used

class Siacontractsdata:
    def __init__(self, json):
        self.__contracts = []
        for json_contract in json['contracts']:
            self.__contracts.append(Siacontractsdata.Contract(json_contract))

    @property
    def contracts(self):
       return self.__contracts 

    class Contract:

        def __init__(self, json):
            self.__datasize = int(json['datasize'])
            self.__locked_collateral = Conversions.hasting_to_siacoin(int(json['lockedcollateral']))
            self.__risked_collateral = Conversions.hasting_to_siacoin(int(json['riskedcollateral']))
            self.__storage_revenue = Conversions.hasting_to_siacoin(int(json['potentialstoragerevenue']))
            self.__io_revenue = Conversions.hasting_to_siacoin(int(json['potentialuploadrevenue'])) + \
                Conversions.hasting_to_siacoin(int(json['potentialdownloadrevenue']))
            self.__ephemeral_revenue = Conversions.hasting_to_siacoin(int(json['potentialaccountfunding']))
            self.__start = int(json['negotiationheight'])
            self.__end = int(json['proofdeadline'])
            self.__proof_success = json['obligationstatus'] == 'obligationSucceeded'

        @property
        def datasize(self):
            return self.__datasize

        @property
        def locked_collateral(self):
            return self.__locked_collateral

        @property
        def risked_collateral(self):
            return self.__risked_collateral

        @property
        def storage_revenue(self):
            return self.__storage_revenue

        @property
        def io_revenue(self):
            return self.__io_revenue

        @property
        def ephemeral_revenue(self):
            return self.__ephemeral_revenue

        @property
        def start(self):
            return self.__start

        @property
        def end(self):
            return self.__end

        @property
        def proof_success(self):
            return self.__proof_success
