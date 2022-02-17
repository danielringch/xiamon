import datetime, os
from ..core.interface import Interface
from ..core import Config

class Logfile(Interface):
    def __init__(self, config, scheduler):
        super(Logfile, self).__init__()
        config_data = Config(config)

        self.__file_handles = {}
        self.__channels = {}

        for channel, name in self.channel_names.items():
            if name in config_data.data:
                file, file_given = config_data.get_value_or_default(None, name, 'file')
                if not file_given:
                    print(f'[logfile] WARNING: Channel {name} ignored, since no file is given.')
                    continue
                handle = self.__file_handles.setdefault(file, Logfile.Filehandle(file))
                self.__channels[channel] = Logfile.Channel(
                    name,
                    handle,
                    config_data.get_value_or_default(None, name, 'whitelist')[0],
                    config_data.get_value_or_default(None, name, 'blacklist')[0])

        scheduler.add_job('logfile-flush', self.__flush, "* * * * *")
        scheduler.add_job('logfile-daychange' ,self.__handle_day_change, '0 0 * * *')

    async def start(self):
        channels = ','.join(self.channel_names[x] for x in self.__channels.keys())
        print(f'[logfile] Logfile ready, available channels: {channels}')

    async def send_message(self, channel, prefix, message):
        if channel not in self.__channels:
            return
        self.__channels[channel].send(prefix, message)

    async def __handle_day_change(self):
        for handle  in self.__file_handles.values():
            handle.close()

    async def __flush(self):
        for file in self.__file_handles.values():
            file.flush()

    class Channel:
        def __init__(self, name, handle, whitelist, blacklist):
            self.__handle = handle
            self.__name = name
            self.__whitelist = set(whitelist) if whitelist is not None else None
            self.__blacklist = set(blacklist) if blacklist is not None else None
            self.__separator = '|'
            self.__handle.write(f'{self.__now()} | Channel {self.__name} is attached to this file.')

        def send(self, prefix, message):
            if self.__whitelist is not None and prefix not in self.__whitelist:
                return
            if self.__blacklist is not None and prefix in self.__blacklist:
                return
            now = self.__now()
            for line in message.splitlines():
                self.__handle.write(f'{now} | {self.__name} | {prefix} {self.__separator} {line}')
            self.__toggle_separator()

        def __toggle_separator(self):
            self.__separator = '|' if self.__separator == '#' else '#'

        @staticmethod
        def __now():
            return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    class Filehandle:
        def __init__(self, path):
            self.__directory = os.path.dirname(path)
            full_filename = os.path.basename(path).split('.', 1)
            self.__filename = full_filename[0]
            self.__fileending = f'.{full_filename[1]}' if len(full_filename) > 1 else ''
            self.__current_handle = self.__create_handle()

        def __del__(self):
            self.close()

        def write(self, line):
            if self.__current_handle == None:
                self.__current_handle = self.__create_handle()
            self.__current_handle.write(line)
            self.__current_handle.write('\n')

        def flush(self):
            if self.__current_handle is None:
                return
            self.__current_handle.flush()

        def close(self):
            if self.__current_handle is None:
                return
            self.__current_handle.close()
            self.__current_handle = None

        def __get_filename(self):
            date = datetime.datetime.now().strftime("%Y%m%d")
            return f'{self.__filename}_{date}{self.__fileending}'

        def __create_handle(self):
            filename = self.__get_filename()
            full_path = os.path.join(self.__directory, filename)
            return open(full_path, 'a')
