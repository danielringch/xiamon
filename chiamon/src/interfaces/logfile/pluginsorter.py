import os, re
from ...core.otherdefaultdict import otherdefaultdict
from .logfilehandle import Logfilehandle

class Pluginsorter:
    def __init__(self, path):
        self.__directory = os.path.dirname(path)
        full_filename = os.path.basename(path).split('.', 1)
        self.__filename = full_filename[0]
        self.__fileending = f'.{full_filename[1]}' if len(full_filename) > 1 else '.txt'
        self.__files = otherdefaultdict(lambda x: self.__create_file(x))

    def write(self, plugin, message):
        file = self.__files[plugin]
        file.write(message)

    def flush(self):
        for file in self.__files.values():
            file.flush()

    def daychange(self):
        for file in self.__files.values():
            file.close()

    def __create_file(self, plugin):
        file = Logfilehandle(self.__directory, self.__get_filename(plugin))
        return file

    def __get_filename(self, plugin):
        plugin = re.sub('[^a-zA-Z0-9]', '_', plugin)
        return f'{self.__filename}_{plugin}{self.__fileending}'
