import datetime, os, re
from ...core.otherdefaultdict import otherdefaultdict
from .logfilehandle import Logfilehandle

class Pluginsorter:
    def __init__(self, path):
        self.__directory = os.path.dirname(path)
        full_filename = os.path.basename(path).split('.', 1)
        self.__filename = full_filename[0]
        self.__fileending = f'.{full_filename[1]}' if len(full_filename) > 1 else '.txt'
        self.__files = otherdefaultdict(lambda x: self.__create_file(x))
        self.__activeplugins = set()

    def write(self, plugin, message):
        file = self.__files[plugin]
        file.write(message)
        self.__activeplugins.add(plugin)

    def flush(self):
        for file in self.__files.values():
            file.flush()

    def daychange(self):
        for plugin, file in self.__files.items():
            if plugin not in self.__activeplugins:
                continue
            self.__write_day_header(file)
        self.__activeplugins.clear()

    def __create_file(self, plugin):
        file = Logfilehandle(self.__directory, self.__get_filename(plugin))
        file.on_file_opened(lambda: self.__write_day_header(file))
        return file

    def __get_filename(self, plugin):
        plugin = re.sub('[^a-zA-Z0-9]', '_', plugin)
        return f'{self.__filename}_{plugin}{self.__fileending}'

    def __write_day_header(self, file):
        file.write(
            f'{"~"*120}\n'
            f'{"#"*54} {datetime.datetime.now().strftime("%d.%m.%Y")} {"#"*54}\n'
        )

