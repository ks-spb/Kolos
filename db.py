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

    def execute(self, query, values):
        self.cur.execute(query, values)
        self.conn.commit()

    def __del__(self):
        self.conn.close()


cursor = Database.instance('my_database.db')