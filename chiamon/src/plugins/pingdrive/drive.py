import os, glob, random, os
from .drivestate import Drivestate

class Drive:

    def __init__(self, device, config):
        self.__stat_file = f"/sys/block/{device}/stat"
        self.alias = config['alias']
        self.__expected_active = config['expected_active']
        self.__path = config['path_to_plots']
        self.__state = Drivestate(int(config['max_idle_time']) - 1)
        self.__sectors_read, self.__sectors_written = self.__get_stats()

    def reset_statistics(self):
        self.__state.reset_statistics()

    def check(self):
        sectors_read, sectors_written = self.__get_stats()

        if sectors_read is None or sectors_written is None:
            self.__state.unavailable()
            message = "drive is unavailable"
        else:
            if sectors_read == self.__sectors_read and sectors_written == self.__sectors_written:
                self.__state.inactive()
                message = f'{self.__state.countdown}m until next ping.'
            else:
                self.__state.active()
                message = 'drive was active.'

            self.__sectors_read = sectors_read
            self.__sectors_written = sectors_written

            if self.__state.ping_outstanding:
                message = self.__ping()

        return f'{self.alias}: {message} | {self.__state.ping_count} pings | {self.__state.active_count}m active'

    def __get_stats(self):
        try:
            with open(self.__stat_file, "r") as raw_stats:
                stats = raw_stats.readline().split()
                sectors_read = int(stats[2])
                sectors_written = int(stats[6])
            return sectors_read, sectors_written
        except Exception:
            return None, None

    def __ping(self):
        if self.__read_plot():
            self.__state.pinged(True)
            return f'ping successful.'
        else:
            self.__state.pinged(False)
            return f'ping failed.'

    def __read_plot(self):
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
            return True
        except Exception:
            return False

    @property
    def online(self):
        return self.__state.online

    @property
    def pings(self):
        return self.__state.ping_count

    @property
    def active_minutes(self):
        return self.__state.active_count

    @property
    def expected_active_minutes(self):
        return self.__expected_active
