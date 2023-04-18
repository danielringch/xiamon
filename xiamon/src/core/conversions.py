import re
from datetime import datetime, timedelta
from enum import Enum

Byteunit = Enum('Byteunit', 'b kb mb gb tb')
prefixes_upwards = {
    "" : 0,
    "k" : 1,
    "M" : 2,
    "G" : 3,
    "T" : 4,
    "P" : 5,
    "E" : 6,
    "Z" : 7,
    "Y" : 8
}
prefixes_downwards = {
    "m" : -1,
    "u" : -2,
    "n" : -3,
    "p" : -4,
    "f" : -5,
    "a" : -6,
    "z" : -7,
    "y" : -8
}

class Conversions:

    @staticmethod
    def byte_to_megabyte(bytes):
        return bytes / 1048576

    @staticmethod
    def byte_to(unit, bytes):
        if unit == Byteunit.b:
            return bytes
        elif unit == Byteunit.kb:
            return bytes / 1024
        elif unit == Byteunit.mb:
            return bytes / (1024 * 1024)
        elif unit == Byteunit.gb:
            return bytes / (1024 * 1024 * 1024)
        else:
            return bytes / (1024 * 1024 * 1024 * 1024)

    @staticmethod 
    def byte_to_auto(bytes, binary=True):
        value, prefix = Conversions.autorange(bytes, 1024 if binary else 1000)
        if not binary or prefix == '':
            unit = f'{prefix}B'
        else:
            unit = f'{prefix}iB'
        return value, unit

    @staticmethod
    def bit_to_auto(bits):
        value, prefix = Conversions.autorange(bits, 1024)
        return value, f'{prefix}bit'
    
    @staticmethod
    def to_byte(bytes, unit, binary=True):
        if unit not in prefixes_upwards:
            return None
        factor = ((1024 if binary else 1000) ** prefixes_upwards[unit])
        return bytes * factor

    @staticmethod
    def mojo_to_xch(mojo):
        return mojo / 1000000000000.0

    @staticmethod
    def xch_to_mojo(xch):
        return xch * 1000000000000

    @staticmethod
    def siacoin_to_auto(siacoins):
        value, prefix = Conversions.autorange(siacoins)
        return value, f'{prefix}SC'

    @staticmethod
    def hasting_to_siacoin(hastings):
        return hastings / 1000000 / 1000000 / 1000000 / 1000000

    @staticmethod
    def siacoin_to_hasting(siacoin):
        return round(siacoin * 1000000 * 1000000) * 1000000 * 1000000

    @staticmethod
    def hastingbyte_to_siacointerabyte(value):
        terabyte = 1000**4
        return float(round(Conversions.hasting_to_siacoin(value * terabyte)))

    @staticmethod
    def siacointerabyte_to_hastingbyte(value):
        terabyte = 1000**4
        return round(Conversions.siacoin_to_hasting(value) / terabyte)

    @staticmethod 
    def hastingsbyteblock_to_siacointerabytemonth(value):
        blocks = Conversions.duration_to_siablocks(timedelta(days=30))
        terabyte = 1000**4
        return float(round(Conversions.hasting_to_siacoin(value * blocks * terabyte)))

    @staticmethod 
    def siacointerabytemonth_to_hastingsbyteblock(value):
        blocks = Conversions.duration_to_siablocks(timedelta(days=30))
        terabyte = 1000**4
        return round(Conversions.siacoin_to_hasting(value) / blocks / terabyte)

    @staticmethod
    def siablocks_to_duration(blocks):
        return timedelta(minutes=(10 * blocks))

    @staticmethod
    def duration_to_siablocks(duration):
        return int(duration.total_seconds() / 600)

    @staticmethod
    def autorange(value, base=1000):
        if value < 1:
            for prefix, exp in prefixes_downwards.items():
                result = value / (base ** exp)
                if result >= 1:
                    return result, prefix
            return 0, ""
        else:
            for prefix, exp in prefixes_upwards.items():
                result = value / (base ** exp)
                if result < 1000:
                    return result, prefix
            raise OverflowError()