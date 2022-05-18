import os, glob, random, os
from ...core import Plugin

__version__ = "0.1.0"

class Drive:

    def __init__(self, drive, config):
        self.__stat_file = f"/sys/block/{drive}/stat"
        self.alias = config['alias']
        self.__path = config['path_to_plots']
        self.__max_idle_time = int(config['max_idle_time']) - 1
        self.__remaining_idle_time = self.__max_idle_time
        self.__sectors_read, self.__sectors_written = self.__get_stats()
        self.__pings_executed = 0
        self.__active_minutes = 0

    def check(self):
        sectors_read, sectors_written = self.__get_stats()

        if sectors_read == self.__sectors_read and sectors_written == self.__sectors_written:
            self.__remaining_idle_time -= 1
            message = f'{self.alias}: {self.__remaining_idle_time} minutes until next ping.'
        else:
            self.__active_minutes += 1
            self.__remaining_idle_time = self.__max_idle_time
            message = f'{self.alias}: drive was active, ping postponed.'

        self.__sectors_read = sectors_read
        self.__sectors_written = sectors_written

        if self.__remaining_idle_time <= 0:
            return self.__ping()
        else:
            return Plugin.Channel.debug, message

    def summary(self):
        pings = self.__pings_executed
        active = self.__active_minutes
        self.__pings_executed = 0
        self.__active_minutes = 0
        return pings, active

    def __get_stats(self):
        with open(self.__stat_file, "r") as raw_stats:
            stats = raw_stats.readline().split()
            sectors_read = int(stats[2])
            sectors_written = int(stats[6])
        return sectors_read, sectors_written

    def __ping(self):
        try:
            plot_files = glob.glob(os.path.join(self.__path, '*.plot'))
            if(not len(plot_files)):
                raise Exception(f'no plot files in path {self.__path}.')
            plot_file = plot_files[random.randrange(0,len(plot_files))]
            file_size = os.path.getsize(plot_file)
            offset = random.randrange(0, max(file_size - 1024, 1))
            file = open(plot_file, "rb")
            file.seek(offset,0)
            _ = file.read(1024)
            self.__pings_executed += 1
            return Plugin.Channel.debug, f'{self.alias}: ping successful.'
        except Exception as e:
            return Plugin.Channel.alert, f'{self.alias}: ping failed, {e}'
