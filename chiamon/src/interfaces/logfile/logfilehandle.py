import os

class Logfilehandle:
    def __init__(self, directory, filename):
        self.__directory = directory
        self.__filename = filename
        self.__current_handle = None # no file will be created if write() is never called
        self.__file_opened_callbacks = []

    def __del__(self):
        self.close()

    def write(self, message):
        if self.__current_handle == None:
            self.__current_handle = self.__create_handle()
            for callback in self.__file_opened_callbacks:
                callback()
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

    def on_file_opened(self, callback):
        self.__file_opened_callbacks.append(callback)

    def __create_handle(self):
        full_path = os.path.join(self.__directory, self.__filename)
        return open(full_path, 'a')
