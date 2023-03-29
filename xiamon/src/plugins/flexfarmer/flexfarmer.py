import datetime, os
from typing import DefaultDict
from pathlib import Path
from ...core import Plugin, Config, Tablerenderer
from .flexfarmerparsers import *

class Flexfarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        config_data = Config(config)
        self.__name = config_data.get('flexfarmer', 'name')
        super(Flexfarmer, self).__init__(self.__name, outputs)
        self.print(f'Plugin flexfarmer; name: {self.__name}')

        self.__scheduler = scheduler

        self.__file = config_data.data['log_file']
        self.__output_path = config_data.data['output_path']

        self.__scheduler.add_job(self.__name ,self.run, config_data.get('0 0 * * *', 'interval'))

    async def run(self):
        with self.message_aggregator():
            oldest_timestamp = self.__scheduler.get_last_execution(self.__name)

            parser = FlexfarmerLogParser()

            with open(self.__file, "r", encoding='latin-1') as stream:
                parser.parse(stream, oldest_timestamp)
            
            self.msg.info(
                f'Accepted partials: {parser.partials_accepted}',
                f'Stale partials: {parser.partials_stale}',
                f'Invalid partials: {parser.partials_invalid}')
            if parser.slow_proofs > 0:
                self.msg.info(f'Slow compressed proofs: {parser.slow_proofs}')

            self.__write_time_table(parser.signage_times, parser.partials_times, parser.slow_proof_times)

        self.__write_errors(parser.warning_lines + parser.failed_lines)

    def __write_time_table(self, signage, partials, slow_compressed):
        max_time = max(max(signage.keys(), default=0), max(partials.keys(), default=0), max(slow_compressed.keys(), default=0))

        total_signage = sum(signage.values())
        total_partials = sum(partials.values())
        total_slow_compressed = sum(slow_compressed.values())

        table = Tablerenderer(['Time', 'SignagePoint', 'Partial', 'SlowCompressedPlot'])

        def print_cell(index, dict, total):
            if index not in dict:
                return ''
            value = dict[i]
            return f'{value} {round((100*value/total), 1):5.1f}%'

        for i in range(0, max_time + 1):
            table.data['Time'].append(f'{i}s')
            table.data['SignagePoint'].append(print_cell(i, signage, total_signage))
            table.data['Partial'].append(print_cell(i, partials, total_partials))
            table.data['SlowCompressedPlot'].append(print_cell(i, slow_compressed, total_slow_compressed))

        self.msg.debug(table.render())

    def __write_errors(self, lines, prefix=''):
        if len(lines) == 0:
            return
        Path(self.__output_path).mkdir(parents=True, exist_ok=True)
        file_name = f'{prefix}flexfarmer_errors_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.txt'
        file = os.path.join(self.__output_path, file_name)
        with open(file, "w") as stream:
            stream.writelines(lines)
