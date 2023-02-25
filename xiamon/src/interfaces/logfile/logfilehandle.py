import os, datetime

class Logfilehandle:
    def __init__(self, directory, filename):
        self.__directory = directory
        self.__filename = filename
        self.__current_handle = None # no file will be created if write() is never called

    def __del__(self):
        self.close()

    def write(self, message):
        if self.__current_handle == None:
            self.__current_handle = self.__create_handle()
            self.__current_handle.write(
                f'{"~"*120}\n'
                f'{"#"*54} {datetime.datetime.now().strftime("%d.%m.%Y")} {"#"*54}\n'
            )
        self.__current_handle.write(message)

    def flush(self):
        if self.__current_handle is None:
            return
        self.__current_handle.flush()

    def close(self):
        if self.__current_handle is None:
            return
        self.__current_handle.close()
        self.__current_handle = None

    def __create_handle(self):
        full_path = os.path.join(self.__directory, self.__filename)
        return open(full_path, 'a')
