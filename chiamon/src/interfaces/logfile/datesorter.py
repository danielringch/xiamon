import datetime, os
from .logfilehandle import Logfilehandle

class Datesorter:
    def __init__(self, path):
        self.__directory = os.path.dirname(path)
        full_filename = os.path.basename(path).split('.', 1)
        self.__filename = full_filename[0]
        self.__fileending = f'.{full_filename[1]}' if len(full_filename) > 1 else '.txt'
        self.__file = None
        self.__new_file()

    def write(self, _, message):
        self.__file.write(message)

    def flush(self):
        self.__file.flush()

    def daychange(self):
        self.__new_file()

    def __get_filename(self):
        date = datetime.datetime.now().strftime("%Y%m%d")
        return f'{self.__filename}_{date}{self.__fileending}'

    def __new_file(self):
        if self.__file is not None:
            self.__file.close()
        self.__file = Logfilehandle(self.__directory, self.__get_filename())
