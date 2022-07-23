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
        return value, f'{prefix}{"iB" if binary else "B"}'

    @staticmethod
    def siacoin_to_auto(siacoins):
        value, prefix = Conversions.autorange(siacoins)
        return value, f'{prefix}SC'

    @staticmethod
    def hasting_to_siacoin(hastings):
        return hastings / 1000000 / 1000000 / 1000000 / 1000000

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