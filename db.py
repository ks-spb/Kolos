import sqlite3

class Database:
    __instance = None

    @staticmethod
    def instance(db_name):
        if Database.__instance == None:
            Database.__instance = Database(db_name)
        return Database.__instance

    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cur = self.conn.cursor()

    def execute(self, query, values=None):
        if values:
            return self.cur.execute(query, values)
        return self.cur.execute(query)

    def __del__(self):
        self.conn.commit()
        self.conn.close()


cursor = Database.instance('Li_db_v1_4.db')