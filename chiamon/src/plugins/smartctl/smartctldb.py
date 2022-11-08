import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from ...core import Plugin
from .smartsnapshot import SmartSnapshot

class Smartctldb():
    __tables = [
        """CREATE TABLE IF NOT EXISTS drive (
            id integer PRIMARY KEY,
            name text NOT NULL,
            UNIQUE(name)
        );""",
        """CREATE TABLE IF NOT EXISTS snapshot (
            id integer PRIMARY KEY,
            drive_id INTEGER NOT NULL,
            timestamp integer NOT NULL,
            FOREIGN KEY (drive_id)
                REFERENCES drive(id)
                ON DELETE CASCADE
        );""",
        """CREATE TABLE IF NOT EXISTS attribute (
            id integer PRIMARY KEY,
            snapshot_id INTEGER NOT NULL,
            attribute integer NOT NULL,
            value NOT NULL,
            FOREIGN KEY (snapshot_id)
                REFERENCES snapshot(id)
                ON DELETE CASCADE
        );"""
    ]

    def __init__(self, plugin, file):
        self.__plugin = plugin
        self.__path = Path(file)
        if not self.__path.parent.exists():
            raise FileNotFoundError(f'Path contains not existing directory: {file}')
        self.__db = sqlite3.connect(self.__path)
        cursor = self.__db.cursor()
        for cmd in self.__tables:
            cursor.execute(cmd)

    def __del__(self):
        self.__db.close()

    def update(self, snapshot):
        drive_command = """INSERT OR IGNORE INTO drive(name)
                        VALUES(?)"""
        drive_id_command = "SELECT id FROM drive WHERE name == '{0}'"
        snapshot_command = """INSERT INTO snapshot(drive_id, timestamp)
                            VALUES(?,?)"""
        snapshot_id_command = "SELECT last_insert_rowid()"
        attribute_command = """INSERT INTO attribute(snapshot_id, attribute, value)
                            VALUES(?,?,?)"""

        cursor = self.__db.cursor()
        cursor.execute(drive_command, (snapshot.identifier,))
        drive_id = cursor.execute(drive_id_command.format(snapshot.identifier)).fetchall()[0][0]

        cursor.execute(snapshot_command, (drive_id, int(datetime.now().timestamp())))
        snapshot_id = cursor.execute(snapshot_id_command).fetchall()[0][0]

        for id, value in snapshot.attributes.items():
            cursor.execute(attribute_command, (snapshot_id, id, value))

        self.__db.commit()

    def get(self, drive, timestamp, tolerance=timedelta(minutes=5)):
        snapshot_command = """SELECT snapshot.id, timestamp FROM snapshot
                            INNER JOIN drive ON drive.id = snapshot.drive_id
                            WHERE drive.name == ? AND snapshot.timestamp <= ?
                            ORDER BY timestamp DESC LIMIT 1;"""
        attribute_command = "SELECT attribute, value FROM attribute WHERE snapshot_id == ?"

        unix_timestamp = int((timestamp - tolerance).timestamp())
        snapshot_rows = self.__get_rows(snapshot_command, (drive, unix_timestamp))

        if snapshot_rows is None:
            self.__plugin.msg.debug(
                f'Failed to get snapshot from history: drive {drive} is not in database or no snapshot older than {unix_timestamp} in database.')
            return None

        real_timestamp = datetime.fromtimestamp(snapshot_rows[0][1])
        
        attribute_rows = self.__get_rows(attribute_command, (snapshot_rows[0][0],))
        if attribute_rows is None:
            self.__plugin.msg.debug(f'Failed to get snapshot from history: snapshot is empty.')
            return None

        return SmartSnapshot.from_history(drive, real_timestamp, dict(attribute_rows))

    def delete_older_than(self, timestamp):
        snapshot_command = """DELETE FROM snapshot
                            WHERE timestamp < ?"""
        drive_command = """DELETE FROM drive
                        WHERE id not in (SELECT drive_id FROM snapshot)"""
        cursor = self.__db.cursor()
        cursor.execute(snapshot_command, (int(timestamp.timestamp()),))
        cursor.execute(drive_command)
        self.__db.commit()

    def __get_rows(self, command, data=tuple()):
        cursor = self.__db.cursor()
        cursor.execute(command, data)
        rows = cursor.fetchall()

        if len(rows) == 0:
            return None
        return rows

    