import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class Siadb():
    __tables = [
        """CREATE TABLE IF NOT EXISTS coinprice (
            id integer PRIMARY KEY,
            timestamp integer NOT NULL,
            price real
        );""",
        """CREATE TABLE IF NOT EXISTS balance (
            id integer PRIMARY KEY,
            timestamp integer NOT NULL,
            free int NOT NULL,
            locked int NOT NULL,
            risked int NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS traffic (
            id integer PRIMARY KEY,
            timestamp int NOT NULL,
            epoch text NOT NULL,
            upload integer NOT NULL,
            download integer NOT_NULL
        );""",
        """CREATE TABLE IF NOT EXISTS contracts (
            id integer PRIMARY KEY,
            timestamp int NOT NULL,
            count int NOT NULL,
            storage integer NOT NULL,
            io integer NOT_NULL,
            ephemeral integer NOT_NULL
        );"""
    ]
    __inserters = {
        'coinprice' : """INSERT INTO coinprice(timestamp, price)
                        VALUES(?,?)""",
        'balance' : """INSERT INTO balance(timestamp, free, locked, risked)
                        VALUES(?,?,?,?)""",
        'traffic' : """INSERT INTO traffic(timestamp, epoch, upload, download)
                        VALUES(?,?,?,?)""",
        'contracts' : """INSERT INTO contracts(timestamp, count, storage, io, ephemeral)
                        VALUES(?,?,?,?,?)"""
    }

    def __init__(self, file):
        self.__path = Path(file)
        if not self.__path.parent.exists():
            raise FileNotFoundError(f'Path contains not existing directory: {file}')
        self.__db = sqlite3.connect(self.__path)
        cursor = self.__db.cursor()
        for cmd in Siadb.__tables:
            cursor.execute(cmd)

    def __del__(self):
        self.__db.close()

    def update_coinprice(self, price):
        self.__add_row('coinprice', (int(datetime.now().timestamp()), price))

    def update_balance(self, free, locked, risked, price):
        self.__add_row('balance', (int(datetime.now().timestamp()), free, locked, risked))

    def update_traffic(self, epoch, upload, download):
        self.__add_row('traffic', (int(datetime.now().timestamp()), epoch, upload, download))

    def update_contracts(self, count, storage, io, ephemeral):
        self.__add_row('contracts', (int(datetime.now().timestamp()), count, storage, io, ephemeral))

    def get_coinprice(self, timestamp):
        command = """SELECT price FROM balance {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0]

    def get_balance(self, timestamp):
        command = """SELECT free, locked, risked FROM balance {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0], row[1], row[2]

    def get_traffic(self, timestamp):
        command = """SELECT epoch, upload, download FROM traffic {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None, None, None
        row = rows[len(rows)//2]
        return row[0], row[1], row[2]

    def get_contracts(self, timestamp):
        command = """SELECT count, storage, io, ephemeral FROM contracts {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None, None, None, None
        row = rows[len(rows)//2]
        return row[0], row[1], row[2], row[3]

    def __add_row(self, table, data):
        self.__db.cursor().execute(Siadb.__inserters[table], data)
        self.__db.commit()

    def __get_rows(self, command):
        cursor = self.__db.cursor()
        cursor.execute(command)
        rows = cursor.fetchall()

        if len(rows) == 0:
            return None
        return rows

    def __create_time_filter(self, timestamp, tolerance=timedelta(minutes=5)):
        unix = int(timestamp.timestamp())
        upper = unix + tolerance.total_seconds()
        lower = unix - tolerance.total_seconds()
        return f'WHERE timestamp < {upper} AND timestamp > {lower}'