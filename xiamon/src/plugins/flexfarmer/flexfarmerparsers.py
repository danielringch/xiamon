import re, ciso8601
from collections import defaultdict
from ...core import Conversions

class FlexfarmerLogParser:
    def __init__(self):
        self.partials_accepted = 0
        self.partials_stale = 0
        self.partials_invalid = 0
        self.slow_proofs = 0

        self.signage_times = {}
        self.partials_times = {}
        self.slow_proof_times = {}

        self.failed_lines = []
        self.warning_lines = []

    def parse(self, stream, timestamp_limit):
        parsers = {
            self.NewSignagePointParser : self.NewSignagePointParser(),
            self.SignagePointProcessedParser: self.SignagePointProcessedParser(),
            self.PartialParser: self.PartialParser(),
            self.SlowCompressedProofParser: self.SlowCompressedProofParser(),
            self.IgnoreParser: self.IgnoreParser(),
            self.InitParser: self.InitParser()
        }

        while True:
            full_line = stream.readline();
            if not full_line:
                break

            if full_line[0] != '[': # not all lines contain timestamps, e.g. when block found
                continue
            timestamp = ciso8601.parse_datetime(full_line[1:11] + 'T' + full_line[12:20])
            if timestamp < timestamp_limit:
                continue
            payload = full_line[21:]
            known_line = False
            for parser in parsers.values():
                if parser.parse(payload):
                    known_line = True
                    break;
            if not known_line:
                self.warning_lines.append(payload)

        parser = parsers[self.SignagePointProcessedParser]
        self.signage_times.update(parser.times)
        self.failed_lines.extend(parser.failed_lines)

        parser = parsers[self.PartialParser]
        self.partials_accepted = parser.valid_partials
        self.partials_stale = parser.stale_partials
        self.partials_invalid = parser.invalid_partials
        self.partials_times.update(parser.times)
        self.warning_lines.extend(parser.unaccepted_lines)
        self.failed_lines.extend(parser.failed_lines)

        parser = parsers[self.SlowCompressedProofParser]
        self.slow_proofs += parser.count
        self.slow_proof_times.update(parser.times)
        self.warning_lines.extend(parser.slow_lines)
        self.failed_lines.extend(parser.failed_lines)

    
    class NewSignagePointParser:
        def parse(self, line):
            return line.startswith('  INFO worker: New signage point')

    class SignagePointProcessedParser:
        def __init__(self):
            self.times = defaultdict(lambda: 0)
            self.failed_lines = []

            self.__plots_regex = re.compile('plots=\\d+')
            self.__elapsed_regex = re.compile('elapsed=[\\d\\.ms]+')

        def parse(self, line):
            if not line.startswith('  INFO worker: Processed signage point'):
                return False
            
            try:
                plots = int(self.__plots_regex.search(line).group(0)[6:])
                if plots == 0:
                    return True

                time = FlexfarmerLogParser.to_seconds(self.__elapsed_regex.search(line).group(0)[8:])
                self.times[round(time + 0.5)] += 1
            except:
                self.failed_lines.append(line)
            return True
        
    class PartialParser:
        def __init__(self):
            self.valid_partials = 0
            self.stale_partials = 0
            self.invalid_partials = 0
            self.times = defaultdict(lambda: 0)
            self.unaccepted_lines = []
            self.failed_lines = []

            self.__size_regex = re.compile('size=\\d+')
            self.__elapsed_regex = re.compile('elapsed=[\\d\\.ms]+')

        def parse(self, line):
            if line.startswith('  INFO pool: Partial accepted'):
                self.valid_partials += self.__evaluate_line(line, True)
            elif line.startswith('  WARN pool: Stale partial'):
                self.stale_partials += self.__evaluate_line(line, False)
            elif line.startswith(' ERROR pool: Partial rejected'):
                self.invalid_partials += self.__evaluate_line(line, False)
            else:
                return False
            
            return True
        
        def __evaluate_line(self, line, accepted):
            partials = 0
            try:
                size = int(self.__size_regex.search(line).group(0)[5:])
                partials = 2 ** (size - 32)

                time = FlexfarmerLogParser.to_seconds(self.__elapsed_regex.search(line).group(0)[8:])
                self.times[round(time + 0.5)] += 1

                if not accepted:
                    self.unaccepted_lines.append(line)
            except:
                self.failed_lines.append(line)
            return partials
        
    class SlowCompressedProofParser:
        def __init__(self):
            self.count = 0
            self.times = defaultdict(lambda: 0)
            self.slow_lines = []
            self.failed_lines = []

            self.__elapsed_regex = re.compile('elapsed=[\\d\\.ms]+')

        def parse(self, line):
            if not line.startswith('  WARN worker: Took too much time to fetch/compute compressed proof of space'):
                return False
            
            try:
                self.count += 1
                time = FlexfarmerLogParser.to_seconds(self.__elapsed_regex.search(line).group(0)[8:])
                self.times[round(time + 0.5)] += 1
                self.slow_lines.append(line)
            except:
                self.failed_lines.append(line)
            return True

    class IgnoreParser:
        def __init__(self):
            self.__lines = [
                '  WARN worker: Detected plot update action=',
                '  WARN plots: Queued plot for later loading',
                '  WARN plots: Attempting to load a previously failed to load',
                '  WARN worker: Removed plot plot=',
                '  INFO worker: Added new plot plot='
                '  INFO plots: Plot loaded successfully',
                '  WARN Shutting down reason=',
                '  INFO Exited'
            ]

        def parse(self, line):
            for start in self.__lines:
                if line.startswith(start):
                    return True
            return False

    class InitParser:
        def __init__(self):
            self.__lines = [
                '  INFO config: Loaded config',
                '  INFO Configured file loggi',
                '  INFO Starting FlexFarmer p',
                '  INFO Configured API server',
                '  INFO worker: Configured au',
                '  WARN worker: Network steal',
                '  INFO worker: Configured fa',
                '  INFO worker: Initializing ',
                '  INFO plots: Initialized pl',
                '  INFO worker: Initialized G',
                '  INFO worker: Connected to '
            ]
        def parse(self, line):
            return line[:28] in self.__lines
        
    # flexfarmer has a non-standard duration notation for values greater 1 minute,
    # so we need an extra parser here
    @staticmethod
    def to_seconds(time):
        match = re.match(r'([\d\.]+m)?([\d\.]+)([ms]+)', time)
        if not match:
            raise ValueError()
        minutes, value, unit = match.group(1,2,3)

        seconds = float(minutes[:-1]) * 60.0 if minutes is not None else 0.0
        if unit == 's':
            seconds += float(value)
        elif unit == 'ms':
            seconds += float(value) / 1000.0
        else:
            raise ValueError()
        return seconds
