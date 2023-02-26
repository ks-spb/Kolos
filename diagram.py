import sqlite3
import contextlib

from diagrams import Diagram, Cluster, Node

"""
Для работ программы на компьютер необходимо установить Graphviz
(https://graphviz.org/download/)
и модуль Python Diagrams
(https://diagrams.mingrammer.com/docs/getting-started/installation)


Группровка точек:

type 'mozg'             - бирюзовый
name 'time', 'time_p'   - желтый
name 'time_0', 't0'     - зеленый
name 'print'            - синий
name 'пло'              - красный (оттенок)
name 'хоро'             - серый

"""


class Point:
    """ Точки """
    def __init__(self, id, name, type):

        self.id = id
        self.name = name
        self.type = type

        if name == 'time' or name == 'time_p':
            # Временные точки входящих сигналов
            self.group = 't'
            color = 'lemonchiffon'

        elif name == 'time_0' or name == 't0':
            # Временные точки
            self.group = 't0'
            color = 'limegreen'

        elif name == 'time_0' or name == 't0':
            # Действия
            self.group = 'action'
            color = 'aqua'

        elif name == 'хоро':
            # Реакция Хорошо
            self.group = 'reaction'
            color = 'salmon'

        elif name == 'пло':
            # Реакция Плохо
            self.group = 'reaction'
            color = 'silver'

        elif type == 'print':
            # Вывод
            self.group = 'out'
            color = 'mediumorchid'

        else:
            # Входящие
            self.group = 'in'
            color = 'cadetblue'

        with Cluster(self.group):
            self.node = Node(f'{id} {name}', style='filled', fillcolor=color, fontsize='20pt')


# Подключение к БД
with contextlib.closing(sqlite3.connect('Li_db_v1_4.db')) as conn:

    nodes = conn.execute("SELECT ID, name, type FROM tochki")
    connections = conn.execute("SELECT id_start, id_finish FROM svyazi WHERE id > 2")

    with Diagram('My Diagram', direction='LR'): # LR или TB

        points = [Point('0', 'time', '')]  # Все точки

        for i in nodes.fetchall():
            points.append(Point(*i))


        for one, two in connections.fetchall():
            points[one].node >> points[two].node

