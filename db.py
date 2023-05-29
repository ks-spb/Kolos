#  Класс для работы с базой данных

import sqlite3
from threading import local


#  Создает новый объект локальных данных потока.
#  Этот объект используется для хранения данных, которые являются локальными для каждого потока.
#  Когда вы обращаетесь к атрибутам этого объекта, вы получаете значения,
#  которые уникальны для текущего потока.
thread_local = local()  # Создаем локальные переменные потока

class Database:

    def __init__(self, db_name):
        """ Запоминаем имя базы данных для подключения """
        self.db_name = db_name

    def get_connection(self):
        """ Получение подключения к БД если среди локальных переменных потока еще нет подключения
        создается новое подключение и сохраняется в локальных переменных потока """
        if not hasattr(thread_local, "db_connection"):
            thread_local.db_connection = sqlite3.connect(self.db_name)
        return thread_local.db_connection

    def execute(self, query, values=None):
        """ Выполнение запроса к БД, если в этом потоке нет подключения, то оно создается """
        conn = self.get_connection()
        cur = conn.cursor()
        if values:
            return cur.execute(query, values)
        return cur.execute(query)

    def __del__(self):
        """ Сохранение изменений в БД и закрытие подключения """
        if hasattr(thread_local, "db_connection"):
            # Если подключение в этом потоке есть, то сохраняем изменения и закрываем подключение
            conn = self.get_connection()
            conn.commit()
            conn.close()

    def commit(self):
        """ Сохранение изменений в БД """
        conn = self.get_connection()
        conn.commit()