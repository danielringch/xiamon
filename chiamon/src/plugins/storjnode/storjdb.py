import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class Storjdb():
    __tables = [
        """CREATE TABLE IF NOT EXISTS balance (
            id integer PRIMARY KEY,
            timestamp integer NOT NULL,
            balance real NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS traffic (
            id integer PRIMARY KEY,
            timestamp integer NOT NULL,
            upload integer NOT NULL,
            download integer NOT NULL,
            repair integer NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS storage (
            id integer PRIMARY KEY,
            timestamp integer NOT NULL,
            storage integer NOT NULL
        );"""
    ]
    __inserters = {
        'balance' : """INSERT INTO balance(timestamp, balance)
                        VALUES(?,?)""",
        'traffic' : """INSERT INTO traffic(timestamp, upload, download, repair)
                        VALUES(?,?,?, ?)""",
        'storage' : """INSERT INTO storage(timestamp, storage)
                        VALUES(?,?)"""
    }

    def __init__(self, file):
        self.__path = Path(file)
        if not self.__path.parent.exists():
            raise FileNotFoundError(f'Path contains not existing directory: {file}')
        self.__db = sqlite3.connect(self.__path)
        cursor = self.__db.cursor()
        for cmd in self.__tables:
            cursor.execute(cmd)

    def __del__(self):
        self.__db.close()

    def update_balance(self, balance):
        self.__add_row('balance', (int(datetime.now().timestamp()), balance))

    def update_traffic(self, upload, download, repair):
        self.__add_row('traffic', (int(datetime.now().timestamp()), upload, download, repair))

    def update_storage(self, storage):
        self.__add_row('storage', (int(datetime.now().timestamp()), storage))

    def get_balance(self, timestamp):
        command = """SELECT balance FROM balance {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0]

    def get_traffic(self, timestamp):
        command = """SELECT upload, download, repair FROM traffic {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None, None, None
        row = rows[len(rows)//2]
        return row[0], row[1], row[2]

    def get_storage(self, timestamp):
        command = """SELECT storage FROM storage {0};"""
        rows = self.__get_rows(command.format(self.__create_time_filter(timestamp)))
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0]

    def __add_row(self, table, data):
        self.__db.cursor().execute(self.__inserters[table], data)
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