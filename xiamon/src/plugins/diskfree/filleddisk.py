import os, shutil, glob
from ...core.conversions import Conversions

class FilledDisk:

    def __init__(self, plugin, path, config):
        self.__plugin = plugin
        self.__path = path
        raw_minimum_space = config['minimum_space']
        if raw_minimum_space.endswith('%'):
            abs_space, _, _ = shutil.disk_usage(self.__path)
            self.__min_space = abs_space * float(raw_minimum_space[:-1]) / 100.0
        else:
            if raw_minimum_space[-1].isdigit():
                unit = ""
                bytes = float(raw_minimum_space)
            else:
                unit = raw_minimum_space[-1]
                bytes = float(raw_minimum_space[:-1])
            self.__min_space = Conversions.to_byte(bytes, unit)
        self.__delete = config.setdefault('delete', None)

    def check(self):
        _, _, free_space = shutil.disk_usage(self.__path)

        if free_space >= self.__min_space:
            self.__plugin.msg.debug('Free space at {0}: {1[0]:.2f} {1[1]}'.format(self.__path, Conversions.byte_to_auto(free_space)))
            self.__plugin.reset_alert(self.__path, f'Free space at {self.__path} meets its minimum value again.')
            return

        missing_space = self.__min_space - free_space

        normalized_free_space = Conversions.byte_to_auto(free_space)
        normalized_min_space = Conversions.bit_to_auto(self.__min_space)
        normalized_missing_space = Conversions.byte_to_auto(missing_space)
        low_space_message = 'Low free space at {0}: {1[0]:.2f} {1[1]} required, {2[0]:.2f} {2[1]} available, {3[0]:.2f} {3[1]} missing.'.format(
            self.__path,
            normalized_min_space,
            normalized_free_space,
            normalized_missing_space
        )
        self.__plugin.msg.debug(low_space_message)

        if not self.__try_delete(missing_space):
            self.__plugin.alert(self.__path, low_space_message)

    def __try_delete(self, missing_space):
        if self.__delete is None:
            return False
        candidates = glob.glob(self.__delete)
        if len(candidates) == 0:
            return False
  
        for candidate in candidates:
            try:
                missing_space -= os.stat(candidate).st_size
                os.remove(candidate)
                delete_message = f'Deleted file {candidate}.'
                self.__plugin.msg.debug(delete_message)
                self.__plugin.msg.info(delete_message)
                if missing_space <= 0:
                    return True
            except:
                self.__plugin.msg.error(f'Failed to delete file {candidate}')
                return False
        return False
   