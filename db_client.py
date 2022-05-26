from logging import Logger, getLogger
import sqlite3

from contextlib import closing

class DBClient:
    logger: Logger

    def __init__(self, path):
        self.path = path
        self.logger = getLogger('amazonPlugin')

    def select(self, table, rows=['*'], where='1'):
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cursor:
                try:
                    cursor.execute(f'SELECT {", ".join(rows)} FROM {table} WHERE {where};')
                    return cursor.fetchall()
                except sqlite3.DatabaseError as e:
                    self.logger.exception(f'DB exception encountered while trying to read rows "{", ".join(rows)}" from table "{table}": {e}')
                    return []
