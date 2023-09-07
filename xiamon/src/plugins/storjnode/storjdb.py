import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

class Storjdb():
    __tables = [
        """CREATE TABLE IF NOT EXISTS node (
            id integer PRIMARY KEY,
            node text NOT NULL,
            UNIQUE(node)
        );""",
        """CREATE TABLE IF NOT EXISTS balance (
            id integer PRIMARY KEY,
            node_id INTEGER NOT NULL,
            timestamp integer NOT NULL,
            balance real NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS traffic (
            id integer PRIMARY KEY,
            node_id INTEGER NOT NULL,
            timestamp integer NOT NULL,
            upload integer NOT NULL,
            download integer NOT NULL,
            repair integer NOT NULL
        );""",
        """CREATE TABLE IF NOT EXISTS storage (
            id integer PRIMARY KEY,
            node_id INTEGER NOT NULL,
            timestamp integer NOT NULL,
            storage integer NOT NULL
        );"""
    ]
    __inserters = {
        'node'    : """INSERT OR IGNORE INTO node(node)
                        VALUES(?)""",
        'balance' : """INSERT INTO balance(node_id, timestamp, balance)
                        VALUES(?,?,?)""",
        'traffic' : """INSERT INTO traffic(node_id, timestamp, upload, download, repair)
                        VALUES(?,?,?,?,?)""",
        'storage' : """INSERT INTO storage(node_id, timestamp, storage)
                        VALUES(?,?,?)"""
    }
    __getters = {
        'balance' : """SELECT balance FROM balance {0};""",
        'traffic' : """SELECT upload, download, repair FROM traffic {0};""",
        'storage' : """SELECT storage FROM storage {0};"""
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

    def update_balance(self, node, balance):
        self.__add_row('balance', node, (int(datetime.now().timestamp()), balance))

    def update_traffic(self, node, upload, download, repair):
        self.__add_row('traffic', node, (int(datetime.now().timestamp()), upload, download, repair))

    def update_storage(self, node, storage):
        self.__add_row('storage', node, (int(datetime.now().timestamp()), storage))

    def get_balance(self, node, timestamp):
        rows = self.__get_rows('balance', node, timestamp)
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0]

    def get_traffic(self, node, timestamp):
        rows = self.__get_rows('traffic', node, timestamp)
        if rows is None:
            return None, None, None
        row = rows[len(rows)//2]
        return row[0], row[1], row[2]

    def get_storage(self, node, timestamp):
        rows = self.__get_rows('storage', node, timestamp)
        if rows is None:
            return None
        row = rows[len(rows)//2]
        return row[0]

    def __add_row(self, table, node, data):
        cursor = self.__db.cursor()
        cursor.execute(self.__inserters['node'], (node,))
        node_id = cursor.execute(f"SELECT id FROM node WHERE node == '{node}'").fetchall()[0][0]
        cursor.execute(self.__inserters[table], (node_id, *data))
        self.__db.commit()

    def __get_rows(self, table, node, timestamp):
        cursor = self.__db.cursor()
        node_id = cursor.execute(f"SELECT id FROM node WHERE node == '{node}'").fetchall()[0][0]
        cursor.execute(self.__getters[table].format(self.__create_time_and_node_filter(node_id, timestamp)))
        rows = cursor.fetchall()

        if len(rows) == 0:
            return None
        return rows

    def __create_time_and_node_filter(self, node, timestamp, tolerance=timedelta(minutes=5)):
        unix = int(timestamp.timestamp())
        upper = unix + tolerance.total_seconds()
        lower = unix - tolerance.total_seconds()
        return f'WHERE node_id == {node} AND timestamp < {upper} AND timestamp > {lower}'