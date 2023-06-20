from db import Database


cursor = Database('Li_db_v1_4.db')


def create_dict(point_list, work_dict=dict()):
    """ Рекурсивная функция получающая все связи в виде словаря из БД """
    for point in point_list:
        points = cursor.execute(
            "SELECT svyazi.id_finish "
            "FROM svyazi JOIN tochki "
            "ON svyazi.id_finish = tochki.id "
            "WHERE svyazi.id_start = ? AND tochki.name = 'time_0'", (point,)).fetchall()
        nodes = [row[0] for row in points]
        if nodes:
            work_dict[point] = nodes
            create_dict(work_dict[point], work_dict)
    return work_dict


def all_paths(tree, node):
    """ Рекурсивная функция получающая все пути из дерева """
    if node not in tree:
        return [[node]]
    paths = []
    for child_node in tree[node]:
        for path in all_paths(tree, child_node):
            paths.append([node] + path)
    return paths

start = 3  # Начальная точка

tree = create_dict([start])  # Получаем выборку связей в виде словаря (дерево)
# print(tree)
print(all_paths(tree, start))
