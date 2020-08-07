import sqlite3

class DBClient:
    def __init__(self, path):
        self.path = path
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row

    def select(self, table, rows=['*'], where='1'):
        cursor = self.con.cursor()
        cursor.execute(f'SELECT {", ".join(rows)} FROM {table} WHERE {where};')
        return cursor.fetchall()
