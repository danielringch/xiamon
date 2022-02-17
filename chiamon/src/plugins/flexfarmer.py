import datetime, ciso8601, re, os
from typing import DefaultDict
from pathlib import Path
from ..core import Plugin, Config

__version__ = "0.4.0"

# TODO: write parser for times. Values > 1 minute have format \d+m[\d\.]+

class Flexfarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        name, _ = config_data.get_value_or_default('flexfarmer', 'name')
        super(Flexfarmer, self).__init__(name, outputs)
        self.print(f'Flexfarmer plugin {__version__}; name: {name}')

        self.__file = config_data.data['log_path']
        self.__aggregation, _ = config_data.get_value_or_default(24, 'aggregation')
        self.__output_path = config_data.data['output_path']
        self.__cleanup, _ = config_data.get_value_or_default(False, 'reset_logs')

        scheduler.add_job(name ,self.run, config_data.get_value_or_default('0 0 * * *', 'interval')[0])

    async def run(self):
        await self.send(Plugin.Channel.debug, f'Creating summary from {self.__file}.')
        oldest_timestamp = datetime.datetime.now() - datetime.timedelta(hours=self.__aggregation)
        parser = Flexfarmer.Parser(oldest_timestamp)

        with open(self.__file, "r") as stream:
            while True:
                full_line = stream.readline();
                if not full_line:
                    break
                parser.parse(full_line)

        message = f'Flexfarmer summary; Aggregation={self.__aggregation}h\n'
        message += f'Accepted partial: {parser.accepted_partial}'
        message = self.__add_statistic(message, 'Stale partial', parser.stale_partial)
        message = self.__add_statistic(message, 'Duplicate partial', parser.duplicate_partial)
        message = self.__add_statistic(message, 'Plot added', parser.plot_added)
        message = self.__add_statistic(message, 'Reverted signage point', parser.reverted_signage_point)
        message = self.__add_statistic(message, 'Region unhealty', parser.region_unhealty)
        message = self.__add_statistic(message, 'Primary region unavailable', parser.primary_region_unavailable)
        message = self.__add_statistic(message, 'Failover region unavailable', parser.failover_region_unavailable)
        message = self.__add_statistic(message, 'Network error', parser.network_error)
        message = self.__add_statistic(message, 'Unknown errors', parser.unknown_error)
        for category, partials in sorted(parser.lookup_times.items(), key=lambda x: x[0]):
            message = self.__add_statistic(message, f'Lookup time < {category + 1}s', partials)

        sending_tasks = self.send(Plugin.Channel.info, message)

        self.__write_errors(parser.error_lines)
        self.__write_errors(parser.unknown_error_lines, 'unknown_')

        if self.__cleanup:
            open(self.__file, 'w').close()

        await sending_tasks

    def __add_statistic(self, message, header, value):
        if value:
            message += f'\n{header}: {value}'
        return message

    def __write_errors(self, lines, prefix=''):
        if len(lines) == 0:
            return
        Path(self.__output_path).mkdir(parents=True, exist_ok=True)
        file_name = f'{prefix}flexfarmer_errors_{datetime.datetime.now().strftime("%m%d%Y%H%M%S")}.txt'
        file = os.path.join(self.__output_path, file_name)
        with open(file, "w") as stream:
            stream.writelines(lines)

    class Parser:
        def __init__(self, oldest_timestamp):
            self.__oldest_timestamp = oldest_timestamp
            self.lookup_times = DefaultDict(lambda: 0)
            self.accepted_partial = 0
            self.stale_partial = 0
            self.plot_added = 0
            self.duplicate_partial = 0
            self.reverted_signage_point = 0
            self.region_unhealty = 0
            self.primary_region_unavailable = 0
            self.failover_region_unavailable = 0
            self.network_error = 0
            self.unknown_error = 0
            self.error_lines = []
            self.unknown_error_lines = []

            self.__parsers = [self.__parse_partial_accepted, self.__parse_lookup,
                              self.__parse_uninteresting,
                              self.__parse_stale_partial, self.__parse_plot_added,
                              self.__parse_duplicate_partial,
                              self.__parse_rejected_partial, self.__parse_unhealty_region,
                              self.__parse_primary_region_unavailable, self.__parse_failover,
                              self.__parse_network_error, self.__parse_farmer_not_initialized]

        def parse(self, line):
            timestamp = ciso8601.parse_datetime(line[1:11] + 'T' + line[12:20])
            if timestamp < self.__oldest_timestamp:
                return
            payload = line[21:]

            parser_found = False
            for parser in self.__parsers:
                is_error = parser(payload)
                if is_error is not None:
                    parser_found = True
                    if is_error is True:
                        self.error_lines.append(line)
                    break
            if not parser_found:
                self.unknown_error += 1
                self.error_lines.append(line)
                self.unknown_error_lines.append(line)

        def __parse_partial_accepted(self, line):
            if line.startswith('  INFO pool: Partial accepted'):
                size_regex = re.compile('size=\\d+')
                size = int(size_regex.search(line).group(0)[5:])
                points = 2 ** (size - 32)
                self.accepted_partial += points
                return False
            return None

        def __parse_lookup(self, line):
            if line.startswith('  INFO worker: Processed signage point'):
                plots_regex = re.compile('plots=\\d+')
                plots = int(plots_regex.search(line).group(0)[6:])
                if plots == 0:
                    return False
                elapsed_regex = re.compile('elapsed=[\\d\\.m]+')
                elapsed = elapsed_regex.search(line).group(0)[8:]
                if elapsed.endswith('m'):
                    time = int(float(elapsed[:-1]))
                else:
                    time = int(float(elapsed) * 1000.0)
                self.lookup_times[int(time / 1000)] += 1
                return False
            return None
                

        def __parse_uninteresting(self, line):
            if line.startswith('  INFO'):
                return False
            return None

        def __parse_stale_partial(self, line):
            if line.startswith('  WARN pool: Stale partial'):
                if 'The partial is too late.' in line:
                    self.stale_partial += 1
                    return True
                else:
                    return None
            return None

        def __parse_plot_added(self, line):
            if line.startswith('  WARN worker: Detected plot update action=CREATE'):
                self.plot_added += 1
                return False
            return None

        def __parse_duplicate_partial(self, line):
            if line.startswith(' ERROR pool: Duplicate partial'):
                self.duplicate_partial += 1
                return True
            return None

        def __parse_rejected_partial(self, line):
            if(line.startswith(' ERROR pool: Partial rejected')):
                if 'Requested signage point was reverted' in line:
                    self.reverted_signage_point += 1
                return True
            return None

        def __parse_unhealty_region(self, line):
            if line.startswith('  WARN health: Region is unhealthy'):
                self.region_unhealty += 1
                return True
            return None

        def __parse_primary_region_unavailable(self, line):
            if line.startswith(' ERROR worker: Failed to connect to the primary Flexpool region'):
                self.primary_region_unavailable += 1
                return True
            return None

        def __parse_failover(self, line):
            if line.startswith('  WARN failover: Activating failover from the primary region endpoint set'):
                return False
            if line.startswith('  WARN failover: Attempting to disable the failover and switch back to the primary region'):
                return False
            if line.startswith('  WARN failover: Selected new failover endpoint set gateway'):
                return False
            if line.startswith('  WARN failover: Falling back to the primary region as no failover regions seem to be up'):
                self.failover_region_unavailable += 1
                return True
            return None

        def __parse_network_error(self, line):
            if line.startswith('  WARN worker: Reconnecting to the blockchain bridge gateway error'):
                self.network_error += 1
                return True
            if line.startswith(' ERROR pool: Failed to make pool request'):
                self.network_error += 1
                return True
            return None

        def __parse_farmer_not_initialized(self, line):
            if line.startswith('  WARN pool: Farmer is not initialized'):
                return False
            return None
