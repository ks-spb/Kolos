"""
Модуль выполняет скриншот изображения и его преобразование в точки
"""

import os, sys
import datetime
import numpy as np
import pyautogui
import cv2
from PIL import Image
import sqlite3
import time


conn = sqlite3.connect('Li_db_v1_4.db')
cursor = conn.cursor()
# Настройки
# REGION должен быть больше, чем 17х17, чтобы можно было один раз сделать скриншот и работать с квадратом 17х17.
# 21 - это 17 + 4 слоя для возможности перемещения.
REGION = 21  # Сторона квадрата с сохраняемым элементом. Ставить нечетным!
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений
thresh = []   # Список, в котором будет храниться обработанное изображение
east = 1
south = 2
south_east = 3
south_west = 4
start = 5

def stiranie_pamyati():
    # Удаление лишних строчек в таблицах БД
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM glaz WHERE ID > 5")
    cursor.execute("DELETE FROM svyazi_glaz WHERE ID > 1")


def screenshot(x_reg: int = 0, y_reg: int = 0, region: int = 0):
    """ Скриншот заданного квадрата или всего экрана

    В качестве аргументов принимает координаты верхней левой точки квадрата и его стороны.
    Если сторона на задана (равна 0) - то делает скриншот всего экрана

    """
    if region:
        image = pyautogui.screenshot(region=(x_reg, y_reg, region, region))  # x, y, x+n, y+n (с верхнего левого угла)
    else:
        image = pyautogui.screenshot()
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


# Функция, проверяющая является ли значение (x, y) точкой контура
# def is_contour_point(x, y, matrix):
#     # Проверяем, что точка (x, y) не находится на краю матрицы
#     if (y == 0) or (y == len(matrix) - 1) or (x == 0) or (x == len(matrix[0]) - 1):
#         return False
#     # Проверяем, все ли соседи (x, y) принадлежат объекту
#     return (matrix[y - 1][x] == 1) and (matrix[y + 1][x] == 1) and (matrix[y][x - 1] == 1) and (
#                 matrix[y][x + 1] == 1)


# def spiral(x, y, n):
#     """ Это функция генератор координат по спирали, вокруг заданной точки.
#
#     Ее надо инициализировать и далее с помощью оператора next получать координаты
#      a = spiral(3, 3, 3)
#      x, y = next(a)
#      x, y координаты центра, n - количество слоев
#
#      """
#     x = [x]
#     y = [y]
#     end = y[0] + n + 1
#     xy = [y, x, y, x]  # у - по вертикали, x - по горизонтали
#     where = [1, 1, -1, -1]  # Движение: вниз, вправо, вверх, налево
#     stop = [xy[i][0]+where[i] for i in range(4)]
#     i = 0
#     while y[0] < end:
#         while True:
#             yield (x[0], y[0])
#             xy[i][0] = xy[i][0] + where[i]
#             if xy[i][0] == stop[i]:
#                 stop[i] = stop[i] + where[i]
#                 break
#         i = (i + 1) % 4


def save_image():
    """
    Функция определяет положение курсора мыши, делает скриншот квадрата с заданными размерами и сохраняет файл с img
    """
    x_pos, y_pos = pyautogui.position()
    # print('Позиция мыши следующая: ', x_pos, y_pos)

    # Делаем скриншот нужного квадрата, где центр - координаты мыши
    # image = screenshot(0.5+x_pos-REGION/2, 0.5+y_pos-REGION/2, REGION)

    # скриншот целого экрана
    image = screenshot()

    x = y = 0
    # w = h = REGION
    h = 30
    w = 30   # в csv-файле показывается 600 цифр, в том числе пробелы и запятые

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    preobrazovanie_img(filename)


# def spiral(x, y, n):
#     """ Это функция генератор, ее надо инициализировать и далее с помощью оператора next получать координаты
#      a = spiral(3, 3, 3)
#      x, y = next(a)
#      x, y координаты центра, n - количество слоев """
#     x = [x]
#     y = [y]
#     end = y[0] + n + 1
#     xy = [y, x, y, x]  # у - по вертикали, x - по горизонтали
#     where = [1, 1, -1, -1]  # Движение: вниз, вправо, вверх, налево
#     stop = [xy[i][0]+where[i] for i in range(4)]
#     i = 0
#     while y[0] < end:
#         while True:
#             yield (x[0], y[0])
#             xy[i][0] = xy[i][0] + where[i]
#             if xy[i][0] == stop[i]:
#                 stop[i] = stop[i] + where[i]
#                 break
#         i = (i + 1) % 4

def preobrazovanie_img(filename):
    """
    Функция открывает файл с сохранённым изображением, преобразовывает в ч/б и сохраняет в csv
    """
    global thresh

    img = np.asarray(Image.open(f'{PATH}/{filename}.png'))

    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

    # сохранение scv файла в цвете в csv:
    # np.savetxt(f"{PATH}/{filename}.csv", img.reshape(REGION, -1), delimiter=",", fmt="%s", header=str(img.shape))

    np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл
    # print('thresh:\n', thresh)

    # TO DO прописать, чтобы центр перемещался на 3 слоя вокруг центра, чтобы поймать более точное изображение
    # TO DO сделать так, чтобы контур прорисовывался без запоздания на 1 шаг и не удалялись горизонтальные линии
    # преобразовываем изображение и оставляем только контур
    # img_kontur = []
    # tochka_old = 0
    # for thresh1 in thresh:
    #     # print("thresh1: ", thresh1)
    #     sloy = []
    #     for thresh2 in thresh1:
    #         # print('thresh2: ', thresh2)
    #         # print('tochka_old: ', tochka_old)
    #         # # если новая точка = старой - то 0, иначе 1.
    #         # print('tochka_new: ', tochka_new)
    #         if thresh2 == tochka_old:
    #             tochka_new = 0
    #             sloy.append(tochka_new)
    #         else:
    #             tochka_new = 1
    #             sloy.append(tochka_new)
    #             tochka_old = thresh2
    #     img_kontur.append(sloy)
    #     print("sloy: ", sloy)
    # print("img_kontur: ", img_kontur)


def sozdat_new_tochky(name, work, type, func, porog, signal, puls, rod1, rod2):
    max_ID = cursor.execute("SELECT MAX(ID) FROM glaz").fetchone()
    new_id = max_ID[0] + 1
    cursor.execute("INSERT INTO glaz VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id, name, work, type, func, porog, signal, puls, rod1, rod2, name))
    return new_id


def sozdat_svyaz(id_start, id_finish, koord_start, koord_finish):
    max_ID_svyazi = tuple(cursor.execute("SELECT MAX(ID) FROM svyazi_glaz"))
    for max_ID_svyazi1 in max_ID_svyazi:
        old_id_svyazi = max_ID_svyazi1[0]
        new_id_svyazi = old_id_svyazi + 1
    cursor.execute("INSERT INTO svyazi_glaz VALUES (?, ?, ?, ?, ?, ?)", (new_id_svyazi, id_start, id_finish, 1,
                                                                         koord_start, koord_finish))


def poisk_posledney_koord (x, y, napravlenie, name_koordinaty):
    # х и у - это координаты точки соседа должны передаваться уже в рассчитанном виде, например: x=i-1 y=j-1
    # napravlenie - это east, south и т.д. east = 1, south = 2 и т.д.
    # name_koordinaty - это name текущей координаты
    name_tochki_i_j_1 = str(x) + '_' + str(y)
    posl_koord_v_cepochke = name_tochki_i_j_1
    poisk_koordinaty = True
    while poisk_koordinaty:
        print(f'Последняя найденная координата такая: {posl_koord_v_cepochke}')
        poisk_posledney = tuple(cursor.execute(
            "SELECT koord_finish FROM svyazi_glaz WHERE koord_start = ? AND koord_finish IS NOT 0",
            (posl_koord_v_cepochke,)))
        print(f"Найдена следующая координата в сетке: {poisk_posledney}")
        if not poisk_posledney:
            poisk_koordinaty = False
        else:
            for poisk_posledney1 in poisk_posledney:
                posl_koord_v_cepochke = poisk_posledney1[0]
        # time.sleep(2)
    print(f'Найдена последняя координата в цепочке - это: {posl_koord_v_cepochke}')
    poisk_svyazi_s_thresh = tuple(
        cursor.execute("SELECT id_finish FROM svyazi_glaz WHERE koord_start = ?",
                       (posl_koord_v_cepochke,)))
    print(f'poisk_svyazi_s_thresh такой: {poisk_svyazi_s_thresh}')
    for poisk_svyazi_s_thresh1 in poisk_svyazi_s_thresh:
        posl_tg = poisk_svyazi_s_thresh1[0]
        # Проверить имеется ли между этой (posl_tg) и (south_west) связывающая точка
        poisk_svyazyushei_tg_s_south_west = tuple(cursor.execute(
            "SELECT ID FROM glaz WHERE rod1 = ? AND rod2 = ?", (napravlenie, posl_tg)))
        if not poisk_svyazyushei_tg_s_south_west:
            new_time_g = sozdat_new_tochky('time_g', 0, 'time', 'zazech_sosedey', 1, 0, 0,
                                           napravlenie, poisk_svyazi_s_thresh1[0])
            sozdat_svyaz(napravlenie, new_time_g, 0, 0)
            sozdat_svyaz(poisk_svyazi_s_thresh1[0], new_time_g, 0, 0)
            sozdat_svyaz(0, new_time_g, name_koordinaty, 0)
            posl_tg = new_time_g
        else:
            for poisk_svyazyushei_tg_s_south_west1 in poisk_svyazyushei_tg_s_south_west:
                posl_tg = poisk_svyazyushei_tg_s_south_west1[0]
                sozdat_svyaz(0, posl_tg, name_koordinaty, 0)
    sozdat_svyaz(0, 0, posl_koord_v_cepochke, name_koordinaty)


def save_to_bd():
    # Функция сохраняет изображение в таблицу glaz, начиная от центральной точки, которая = REGION/2+0.5,
    # но перед этим определяет, что находится в центре - если это фон - то ищется точка объекта по спирали
    global thresh
    global REGION

    thresh[thresh == 255] = 1  # Меняем в массиве 255 на 1

    # Определяем, что является чернилами
    ink = 1 if sum(np.sum(i == 1) for i in thresh) < (len(thresh) * len(thresh[0])) // 2 else 0

    # Меняем чернила на 1, а фон на 0
    if not ink:
        mask = thresh ^ 1
        thresh = mask.astype(np.uint8)


    filename = "Preobrazovanniy"

    np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")

    # Печать матрицы
    # for i in thresh:
    #     for j in range(len(i)):
    #         if i[j] == 1:
    #             print("\033[31m {}".format('0'), end='')
    #         elif i[j] == 9:
    #             print("\033[33m {}".format('0'), end='')
    #         else:
    #             print("\033[39m {}".format('0'), end='')
    #     print()

    # Новая пустая матрица
    # matrix = np.copy(thresh)

    # Находим контур объекта
    # for y in range(len(thresh)):
    #     for x in range(len(thresh[y])):
    #         if thresh[y][x] == 1 and is_contour_point(x, y, thresh):
    #             matrix[y][x] = 0

    # Поиск точки в центре которая принадлежит объекту
    # koordinata = REGION // 2  # Делим без остатка
    # sp = spiral(koordinata, koordinata, 3)
    # x, y = next(sp)
    # while matrix[y][x] == 0:
    #     try:
    #         x, y = next(sp)
    #     except:
    #         raise ('Точка не найдена')

    # print(f'x={x}, y={y}')
    # matrix[y][x] = 9

    # Печать матрицы
    # for i in matrix:
    #     for j in range(len(i)):
    #         if i[j] == 1:
    #             print("\033[31m {}".format('0'), end='')
    #         elif i[j] == 9:
    #             print("\033[33m {}".format('0'), end='')
    #         else:
    #             print("\033[39m {}".format('0'), end='')
    #     print()

    # Ищем по часовой стрелке соседнюю горящую (.), чтобы сохранить в БД, начинаем с центральной точки.
    # new_sp = spiral(x, y, 1)
    # new_x, new_y = next(new_sp)
    # new_matrix = matrix
    # print(f'соседний х = {new_x}, y = {new_y}')
    # # print('new_matrix: \n', new_matrix)
    #

    """
    Далее разбор массива thresh, который пройдётся по точкам и запишет уникальный объект в БД.
    Имеются точки сетки. Каждой координате (x,y) соответствует своя точка сетки, но они не записываются в БД.
    Имеются внутренние точки таблицы (glaz), описывающие направление перемещения: (start), (east), (south), (south_east),
    (south_west).
    Имеются внутренние временные точки (tg).
    1. Перебираем лист сохранённого изображения последовательно (слева направо, сверху вниз). Ищем 1.
    2. Если находим точку == 1 - проверка имеется ли к текущей координатной точке соединение koord_finish от другой 
        координатной точки.
        2.1. Если нет - это либо start, либо пропущенный участок при обходе:      
            2.2.1. Проверить есть ли соседи сверху справа (северо-восток); сверху; слева сверху (северо-запад);
            2.2.2. Если горящая точка не находится ни в одном из этих направлений - то текущая точка - связывается с 
            точкой (start), назначить posl_tg = ID (start). Posl_tg - это последняя горящая точка (tg)
            2.2.3. Если была найдена точка == 1 в этих координатах:
                2.2.3.1. Проверить имеется ли у найденной точки связь с другой точкой сетки, где начало стрелки - это 
                          найденная точка, так найти последнюю точку в цепочке
                2.2.3.2. Найти связь с tg у этой последней точки сетки
                2.2.3.3. Присвоить posl_tg этой точке tg
                2.2.3.4. Создать связь с найденной последней точкой сетки и текущей точкой сетки (направление
                         от последней к текущей)
                2.2.3.5. Проверить имеется ли связывающая (tg) между posl_tg и текущей точкой направления
                        2.2.3.5.1. Если да - то зажечь эту (tg) и присвоить ей posl_tg
                        2.2.3.5.2. Если нет - то создать новую точку (tg), соединив posl_tg и горящую точку направления,
                                    присвоить этой новой (tg) posl_tg
        2.2 Если да - проверка имеется ли у этой точки соединение koord_start к другой точке
            2.2.1. Если нет - проверяем имеется ли у текущей координатной точки соседи (по часовой стрелке начало 
                    сверху): сверху, сверху справа; справа; справа снизу; снизу; снизу слева; слева; сверху слева.
                    2.2.1.1. Если да - проверить имеется ли у этой (.) связь koord_finish
                    2.2.1.2. Если имеется - перейти к поиску соседа в следующей координате
                    2.2.1.3. Если не имеется - создать связь с текущей координатой в сетке
                    2.2.1.4. Создать (tg), если не имеется связующей (tg) между posl_tg и новым направлением. Если 
                                имеется - присвоить этому posl_tg = tg
                    2.2.1.5. Создать связь м/у найденной координатной точкой и (tg)
                    2.2.1.6. Перейти к этой (.) и выполнить п. 2.2.1
            2.2.2. Если да - перейти к другой точке в слое.
    3. Когда находим 0 - то присваиваем posl_tg = 0.
    """
    posl_tg = 0
    # Перебор строк матрицы
    for i in range(len(thresh)):
        # Перебор элементов в строке
        for j in range(len(thresh[i])):
            if thresh[i][j] == 1:
                # print(f"Координаты: (y = {i}, x = {j})")
                name_tochki = str(j) + '_' + str(i)
                print(f"Имя точки следующее: {name_tochki}")
                # перебор ближайших (...) на предмет наличия горящих соседей - если нет - то эта точка start,
                # а если есть - то создать связь между текущей точкой и (tg) предыдущей точки.
                if thresh[i][j-1] == 1:   # если найдена точка слева - это east (1).
                    # поиск связи между этой координатной (.) и (tg)
                    name_tochki_i_j_1 = str(j-1) + '_' + str(i)
                    poisk_svyazi = tuple(cursor.execute("SELECT id_finish FROM svyazi_glaz WHERE koord_start = ?",
                                                        (name_tochki_i_j_1,)))
                    # print(f"Нашли связующую точку: {poisk_svyazi} между east (1) и координатной точкой: ",
                    #       name_tochki)
                    # Проверить имеется ли между этой (posl_tg) и (east) связывающая точка
                    for poisk_svyazi1 in poisk_svyazi:
                        poisk_svyazyushei_tg_s_east = tuple(cursor.execute(
                        "SELECT ID FROM glaz WHERE rod1 = 1 AND rod2 = ?", poisk_svyazi1))
                        if not poisk_svyazyushei_tg_s_east:
                            new_time_g = sozdat_new_tochky('time_g', 0, 'time', 'zazech_sosedey', 1, 0, 0, 1,
                                                           poisk_svyazi1[0])
                            sozdat_svyaz(1, new_time_g, 0, 0)
                            sozdat_svyaz(poisk_svyazi1[0], new_time_g, 0, 0)
                            sozdat_svyaz(0, new_time_g, name_tochki, 0)
                            posl_tg = new_time_g
                        else:
                            for poisk_svyazyushei_tg_s_east1 in poisk_svyazyushei_tg_s_east:
                                posl_tg = poisk_svyazyushei_tg_s_east1[0]
                                sozdat_svyaz(0, posl_tg, name_tochki, 0)
                    sozdat_svyaz(0, 0, name_tochki_i_j_1, name_tochki)
                elif thresh[i-1][j+1] == 1:   # если найдена точка сверху справа - это south_west (4)
                    # найти последнюю точку в цепочке связей по координатам
                    poisk_posledney_koord(j + 1, i - 1, south_west, name_tochki)
                elif thresh[i-1][j] == 1:   # если найдена точка сверху - это south (2)
                    poisk_posledney_koord(j, i - 1, south, name_tochki)
                elif thresh[i-1][j-1] == 1:   # если найдена точка сверху слева - это south_east (3)
                    poisk_posledney_koord(j - 1, i - 1, south_east, name_tochki)
                else:
                    # не найдены соседи - значит присвоить posl_tg = start
                    posl_tg = 5
                    sozdat_svyaz(0, posl_tg, name_tochki, 0)
            else:
                posl_tg = 0



stiranie_pamyati()
save_image()
save_to_bd()

conn.commit()

conn.close()
