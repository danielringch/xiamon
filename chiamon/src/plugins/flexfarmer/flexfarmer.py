import datetime, ciso8601, os
from typing import DefaultDict
from pathlib import Path
from ...core import Plugin, Config
from .flexfarmerparsers import *

class Flexfarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        self.__name = config_data.get('flexfarmer', 'name')
        super(Flexfarmer, self).__init__(self.__name, outputs)
        self.print(f'Plugin flexfarmer; name: {self.__name}')

        self.__scheduler = scheduler

        self.__signage_point_parser = SignagePointParser()
        self.__partial_accepted_parser = PartialAcceptedParser()
        self.__partial_stale_parser = PartialStaleParser()
        self.__partial_invalid_parser = PartialInvalidParser()

        self.__parsers = [
            self.__signage_point_parser,
            self.__partial_accepted_parser,
            self.__partial_stale_parser,
            self.__partial_invalid_parser,
            ErrorParser(),
            WarningParser()
        ]

        self.__file = config_data.data['log_path']
        self.__output_path = config_data.data['output_path']
        self.__cleanup = config_data.get(False, 'reset_logs')

        self.__scheduler.add_job(self.__name ,self.run, config_data.get('0 0 * * *', 'interval'))

    async def run(self):
        oldest_timestamp = self.__scheduler.get_last_execution(self.__name)

        with open(self.__file, "r") as stream:
            error_lines, warning_lines = self.__parse_log(stream, oldest_timestamp)
            
        message = []

        message.append(f'Accepted partials: {self.__partial_accepted_parser.partials}')
        message.append(f'Stale partials: {self.__partial_stale_parser.partials}')
        message.append(f'Invalid partials: {self.__partial_invalid_parser.partials}')
        message.extend(self.__evaluate_lookup_times(self.__signage_point_parser.times))

        self.send(Plugin.Channel.info, '\n'.join(message))

        self.__write_errors(error_lines + warning_lines)

        if self.__cleanup:
            open(self.__file, 'w').close()

        for parser in self.__parsers:
            parser.reset()

    def __parse_log(self, stream, timestamp_limit):
        error_lines = []
        warning_lines = []

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
            for parser in self.__parsers:
                type = parser.parse(payload)
                if type == FlexfarmerLogType.unknown:
                    continue
                elif type == FlexfarmerLogType.info:
                    continue
                elif type == FlexfarmerLogType.warning:
                    warning_lines.append(full_line)
                else:
                    error_lines.append(full_line)

        return error_lines, warning_lines

    def __evaluate_lookup_times(self, times):
        lines = []
        total_lookups = sum(times.values())
        for i in range(0,11):
            if i in self.__signage_point_parser.times.keys():
                count = self.__signage_point_parser.times[i]
                lines.append(f'Lookup time < {i}s: {count} ({round((100*count/total_lookups), 1)}%)')
        if 11 in self.__signage_point_parser.times.keys():
            count = self.__signage_point_parser.times[11]
            lines.append(f'Lookup time > 10s: {count} ({round((100*count/total_lookups), 1)}%)')
        return lines

    def __write_errors(self, lines, prefix=''):
        if len(lines) == 0:
            return
        Path(self.__output_path).mkdir(parents=True, exist_ok=True)
        file_name = f'{prefix}flexfarmer_errors_{datetime.datetime.now().strftime("%m%d%Y%H%M%S")}.txt'
        file = os.path.join(self.__output_path, file_name)
        with open(file, "w") as stream:
            stream.writelines(lines)
