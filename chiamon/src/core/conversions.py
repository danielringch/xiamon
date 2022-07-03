from datetime import datetime, timedelta
from enum import Enum

Byteunit = Enum('Byteunit', 'b kb mb gb tb')

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
    def hasting_to_siacoin(hastings):
        return hastings / 1000000 / 1000000 / 1000000 / 1000000

    @staticmethod
    def siablocks_to_duration(blocks):
        return timedelta(minutes=(10 * blocks))

    @staticmethod
    def duration_to_siablocks(duration):
        return int(duration.total_seconds() / 600)
    