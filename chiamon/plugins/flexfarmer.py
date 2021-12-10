import asyncio
import yaml, datetime, ciso8601
from .plugin import Plugin

__version__ = "0.1.0"

class Flexfarmer(Plugin):
    def __init__(self, config, scheduler, outputs):
        super(Flexfarmer, self).__init__('flexfarmer')
        self.print(f'Flexfarmer plugin {__version__}')
        with open(config, "r") as stream:
            config_data = yaml.safe_load(stream)
            self.__log_path = config_data['log_path']

        self.__outputs = outputs

        self.__file = config_data['log_path']
        self.__aggregation = config_data['aggregation']
        self.print(f'Log file to read: {self.__file}', True)

        if "reset_logs" in config_data:
            self.__cleanup = config_data['reset_logs']
        else:
            self.__cleanup = False

        scheduler.add_job("Flexfarmer" ,self.run, config_data['intervall'])

    async def run(self):
        error_lines = []
        partials = 0

        oldest_timestamp = datetime.datetime.now() - datetime.timedelta(hours=self.__aggregation)
        with open(self.__file, "r") as stream:
            while True:
                full_line = stream.readline();
                if not full_line:
                    break
                line = full_line[1:11] + 'T' + full_line[12:20]
                line_timestamp = ciso8601.parse_datetime(line)
                if(line_timestamp < oldest_timestamp):
                    continue
                if 'ERROR' in full_line:
                    error_lines.append(full_line)
                elif 'Partial accepted' in full_line:
                    partials = partials + 1

        message = f'Flexfarmer summary; Aggregation={self.__aggregation}h\n'
        message += f'Accepted partials: {partials}\n'
        message += f'Errors: {len(error_lines)}\n'
        for error_line in error_lines:
            message += error_line

        sending_tasks = []
        for output in self.__outputs:
            sending_tasks.append(output.send_message(message))

        if self.__cleanup:
            open(self.__file, 'w').close()

        await asyncio.gather(*sending_tasks)

