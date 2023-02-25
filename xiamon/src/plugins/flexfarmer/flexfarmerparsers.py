import re
from collections import defaultdict
from typing import DefaultDict
from enum import Enum

FlexfarmerLogType = Enum('FlexfarmerLogType', 'unknown error warning info')

class SignagePointParser:
    def __init__(self):
        self.__times = defaultdict(lambda: 0)

    def parse(self, line):
        if line.startswith('  INFO worker: Processed signage point'):
            plots_regex = re.compile('plots=\\d+')
            plots = int(plots_regex.search(line).group(0)[6:])
            if plots == 0:
                return FlexfarmerLogType.info
            elapsed_regex = re.compile('elapsed=\\d+\\.?\\d*(s|ms)')
            elapsed = elapsed_regex.search(line).group(0)[8:]
            if elapsed is None:
                self.__times[11] += 1
            else:
                try:
                    if elapsed.endswith('ms'):
                        self.__times[0] += 1
                    else:
                        time = int(round(float(elapsed[:-1]) + 0.5))
                        time = min(time, 11)
                        self.__times[time] += 1
                except:
                    self.__times[11] += 1
            return FlexfarmerLogType.info
        return FlexfarmerLogType.unknown

    def reset(self):
        self.__times = defaultdict(lambda: 0)

    @property
    def times(self):
        return self.__times

class PartialAcceptedParser:
    def __init__(self):
        self.__point = 0
        self.__partials = 0

    def parse(self, line):
        if line.startswith('  INFO pool: Partial accepted'):
            size_regex = re.compile('size=\\d+')
            size = int(size_regex.search(line).group(0)[5:])
            points = 2 ** (size - 32)
            self.__partials += points
            return FlexfarmerLogType.info
        return FlexfarmerLogType.unknown

    def reset(self):
        self.__point = 0
        self.__partials = 0

    @property
    def partials(self):
        return self.__partials

class PartialStaleParser:
    def __init__(self):
        self.__count = 0

    def parse(self, line):
        if line.startswith('  WARN pool: Stale partial'):
            self.__count += 1
            return FlexfarmerLogType.error
        return FlexfarmerLogType.unknown

    def reset(self):
        self.__count = 0

    @property
    def partials(self):
        return self.__count

class PartialInvalidParser:
    def __init__(self):
        self.__count = 0

    def parse(self, line):
        if line.startswith(' ERROR pool: Partial rejected'):
            self.__count += 1
            return FlexfarmerLogType.error
        return FlexfarmerLogType.unknown

    def reset(self):
        self.__count = 0

    @property
    def partials(self):
        return self.__count

class ErrorParser:
    def parse(self, line):
        if line.startswith(' ERROR'):
            return FlexfarmerLogType.error
        return FlexfarmerLogType.unknown

    def reset(self):
        pass

class WarningParser:
    def parse(self, line):
        if line.startswith('  WARN'):
            return FlexfarmerLogType.warning
        return FlexfarmerLogType.unknown

    def reset(self):
        pass
