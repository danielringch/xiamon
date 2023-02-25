import os
from datetime import datetime

# csv format:
# date; delta; balance; price

class CsvExporter:
    def __init__(self, file):
        self.__file = file

    def add_line(self, data):
        if self.__file is None:
            return
        
        try:
            is_empty = os.path.getsize(self.__file) == 0
        except:
            is_empty = True

        with open(self.__file, "a+") as csv_file:
            if is_empty:
                self.__add_header(csv_file, data)
            csv_file.write(datetime.now().strftime("%d.%m.%Y %H:%M") 
                + ';' 
                + ';'.join(str(x) for x in data.values())
                + '\n')

    @staticmethod
    def __add_header(file, data):
        file.write('Timestamp;' + ';'.join(data.keys()) + '\n')