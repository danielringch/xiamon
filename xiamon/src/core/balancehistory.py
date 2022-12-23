import csv
from datetime import date, timedelta

# csv format:
# date; delta; balance; price

class Balancehistory:
    def __init__(self, file):
        self.__file = file

    def get_balance(self, date):
        date_string = self.__get_date_string(date)
        try:
            with open(self.__file, "r", newline='') as csv_file:
                reader = csv.reader(csv_file)
                result = None
                for row in reader:
                    if row[0] == date_string:
                        result = float(row[2])
                    elif result is not None:
                        break
                return result
        except FileNotFoundError:
            return None

    def add_balance(self, date, delta, balance, price):
        with open(self.__file, "a+", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([self.__get_date_string(date), delta, balance, price])

    def __get_date_string(self, date):
        return date.strftime("%d.%m.%Y")
