import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class Opendtudb():
    def __init__(self, file):
        self.__path = Path(file)
        if not self.__path.parent.exists():
            raise FileNotFoundError(f'Path contains not existing directory: {file}')
        self.__db = sqlite3.connect(self.__path)
        self.__create_table()

    def __del__(self):
        self.__db.close()

    def __create_table(self):
        command = """CREATE TABLE IF NOT EXISTS energy (
                        id integer PRIMARY KEY,
                        timestamp integer NOT NULL,
                        energy int NOT NULL
                    );"""

        self.__db.cursor().execute(command)

    def add(self, energy):
        command = """INSERT INTO energy(timestamp, energy)
                        VALUES(?,?)"""
        data = (int(datetime.now().timestamp()), energy)

        self.__db.cursor().execute(command, data)
        self.__db.commit()

    def get_latest(self):
        command = """SELECT energy FROM energy ORDER BY timestamp DESC LIMIT 1;"""

        cursor = self.__db.cursor()
        cursor.execute(command)
        rows = cursor.fetchall()

        if len(rows) != 1:
            return None
        return rows[0][0]
    
    def get_since(self, timestamp, tolerance=timedelta(minutes=1)):
        unix = int(timestamp.timestamp())
        unix += tolerance.total_seconds()

        cursor = self.__db.cursor()
        
        ts_command = f'SELECT timestamp FROM energy WHERE timestamp < {unix} ORDER BY timestamp DESC LIMIT 1'
        cursor.execute(ts_command)
        rows = cursor.fetchall()
        if len(rows) != 1:
            return None
        real_ts = rows[0][0]

        command = f'SELECT timestamp, energy FROM energy WHERE timestamp >= {real_ts} ORDER BY timestamp ASC'
        cursor.execute(command)
        rows = cursor.fetchall()

        if len(rows) == 0:
            return None
        result = []
        return [(datetime.fromtimestamp(row[0]), row[1]) for row in rows]
