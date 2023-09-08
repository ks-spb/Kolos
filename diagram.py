import sqlite3
import contextlib
import re

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

# Включить/выключить отображение групп IN и OUT
point_in = False
point_out = False

class Point:
    """ Точки """

    delete_nodes = list()  # Список точек, которые необходимо удалить

    def __init__(self, id, name, type, name_2):

        self.id = id
        self.name = name
        self.type = type
        self.name_2 = name_2

        if name == 'time' or name == 'time_p':
            # Временные точки входящих сигналов
            name = name.replace('time', 't')
            self.group = 't'
            color = 'lemonchiffon'

        elif name == 'time_0' or name == 't0':
            # Временные точки
            name = name.replace('time', 't')
            self.group = 't0'
            color = 'limegreen'

        elif name == 'time_0' or name == 't0':
            # Действия
            name = name.replace('time', 't')
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
            if not point_out:
                self.delete_nodes.append(id)
                raise
            self.group = 'out'
            color = 'mediumorchid'

        else:
            # Входящие
            if not point_in:
                self.delete_nodes.append(id)
                raise
            self.group = 'in'
            color = 'cadetblue'

        with Cluster(self.group):
            self.node = Node(f'{id} {name} {name_2}', style='filled', fillcolor=color, fontsize='20pt')


# Подключение к БД
with contextlib.closing(sqlite3.connect('Li_db_v1_4.db')) as conn:

    # 15.03.23 - добавлено name2
    nodes = conn.execute("SELECT ID, name, type, name2 FROM tochki")
    connections = conn.execute("SELECT id_start, id_finish FROM svyazi WHERE id > 2")

    with Diagram('My Diagram', direction='TB'):  # LR или TB

        points = {0: Point('0', 'time', '', "")}

        for db_tuple in nodes.fetchall():
            # Сокращаем названия событий
            to_obj = list()
            for i in db_tuple:
                if type(i).__name__ == 'str':

                    i = i.replace('Button', 'B').replace('Key', 'K').replace('down', 'd').replace('up', 'u')

                    # Замена названия файла картинки на img
                    if i[:4] == 'elem':
                        i = 'img'

                    # Удаление координат
                    i = re.sub(r'\d+.\d+', '', i)

                to_obj.append(i)
            try:
                points[to_obj[0]] = Point(*to_obj)
            except:
                # При создании объекта возникло исключение
                pass

        for one, two in connections.fetchall():
            if one in Point.delete_nodes or two in Point.delete_nodes:
                continue
            points[one].node >> points[two].node
