import sqlite3
from pathlib import Path
from datetime import datetime

from ...core import Conversions

class Chiawalletdb():
    def __init__(self, file):
        self.__path = Path(file)
        if not self.__path.parent.exists():
            raise FileNotFoundError(f'Path contains not existing directory: {file}')
        self.__db = sqlite3.connect(self.__path)
        self.__create_table()
        self.__balance = self.__get_balance()

    def __del__(self):
        self.__db.close()

    def update_balance(self, balance, price):
        self.__add_row(datetime.now(), balance, price)
        self.__balance = balance

    @property
    def balance(self):
        return self.__balance;

    def __create_table(self):
        command = """CREATE TABLE IF NOT EXISTS balance (
                        id integer PRIMARY KEY,
                        timestamp integer NOT NULL,
                        balance int NOT NULL,
                        price real
                    );"""

        self.__db.cursor().execute(command)

    def __add_row(self, timestamp, balance, price):
        command = """INSERT INTO balance(timestamp, balance, price)
                        VALUES(?,?,?)"""
        data = (int(timestamp.timestamp()), Conversions.xch_to_mojo(balance), price)

        self.__db.cursor().execute(command, data)
        self.__db.commit()

    def __get_balance(self):
        command = """SELECT balance FROM balance ORDER BY timestamp DESC LIMIT 1;"""

        cursor = self.__db.cursor()
        cursor.execute(command)
        rows = cursor.fetchall()

        if len(rows) == 0:
            return None
        return Conversions.mojo_to_xch(rows[0][0])