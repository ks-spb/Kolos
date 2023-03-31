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


conn = sqlite3.connect('Li_db_v1_4.db')
cursor = conn.cursor()
# Настройки
# REGION должен быть больше, чем 17х17, чтобы можно было один раз сделать скриншот и работать с квадратом 17х17.
# 21 - это 17 + 4 слоя для возможности перемещения.
REGION = 17  # Сторона квадрата с сохраняемым элементом. Ставить нечетным!
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений
thresh = []   # Список, в котором будет храниться обработанное изображение


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
def is_contour_point(x, y, matrix):
    # Проверяем, что точка (x, y) не находится на краю матрицы
    if (y == 0) or (y == len(matrix) - 1) or (x == 0) or (x == len(matrix[0]) - 1):
        return False
    # Проверяем, все ли соседи (x, y) принадлежат объекту
    return (matrix[y - 1][x] == 1) and (matrix[y + 1][x] == 1) and (matrix[y][x - 1] == 1) and (
                matrix[y][x + 1] == 1)


def spiral(x, y, n):
    """ Это функция генератор координат по спирали, вокруг заданной точки.

    Ее надо инициализировать и далее с помощью оператора next получать координаты
     a = spiral(3, 3, 3)
     x, y = next(a)
     x, y координаты центра, n - количество слоев

     """
    x = [x]
    y = [y]
    end = y[0] + n + 1
    xy = [y, x, y, x]  # у - по вертикали, x - по горизонтали
    where = [1, 1, -1, -1]  # Движение: вниз, вправо, вверх, налево
    stop = [xy[i][0]+where[i] for i in range(4)]
    i = 0
    while y[0] < end:
        while True:
            yield (x[0], y[0])
            xy[i][0] = xy[i][0] + where[i]
            if xy[i][0] == stop[i]:
                stop[i] = stop[i] + where[i]
                break
        i = (i + 1) % 4


def save_image():
    """
    Функция определяет положение курсора мыши, делает скриншот квадрата с заданными размерами и сохраняет файл с img
    """
    x_pos, y_pos = pyautogui.position()
    # print('Позиция мыши следующая: ', x_pos, y_pos)

    # Делаем скриншот нужного квадрата
    image = screenshot(0.5+x_pos-REGION/2, 0.5+y_pos-REGION/2, REGION)

    x = y = 0
    w = h = REGION

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    preobrazovanie_img(filename)


def spiral(x, y, n):
    """ Это функция генератор, ее надо инициализировать и далее с помощью оператора next получать координаты
     a = spiral(3, 3, 3)
     x, y = next(a)
     x, y координаты центра, n - количество слоев """
    x = [x]
    y = [y]
    end = y[0] + n + 1
    xy = [y, x, y, x]  # у - по вертикали, x - по горизонтали
    where = [1, 1, -1, -1]  # Движение: вниз, вправо, вверх, налево
    stop = [xy[i][0]+where[i] for i in range(4)]
    i = 0
    while y[0] < end:
        while True:
            yield (x[0], y[0])
            xy[i][0] = xy[i][0] + where[i]
            if xy[i][0] == stop[i]:
                stop[i] = stop[i] + where[i]
                break
        i = (i + 1) % 4

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

    # np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл
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


def safe_to_bd():
    # Функция сохраняет изображение в таблицу glaz, начиная от центральной точки, которая = REGION/2+0.5,
    # но перед этим определяет, что находится в центре - если это фон - то ищется точка объекта по спирали
    # TO DO определить какого цвета в изображении больше
    global thresh
    global REGION

    thresh[thresh == 255] = 1  # Меняем в массиве 255 на 1

    # Определяем, что является чернилами
    ink = 1 if sum(np.sum(i == 1) for i in thresh) < (len(thresh) * len(thresh[0])) // 2 else 0

    # Меняем чернила на 1, а фон на 0
    if not ink:
        mask = thresh ^ 1
        thresh = mask.astype(np.uint8)


    # Печать матрицы
    for i in thresh:
        for j in range(len(i)):
            if i[j] == 1:
                print("\033[31m {}".format('0'), end='')
            elif i[j] == 9:
                print("\033[33m {}".format('0'), end='')
            else:
                print("\033[39m {}".format('0'), end='')
        print()

    # Новая пустая матрица
    matrix = np.copy(thresh)

    # Находим контур объекта
    for y in range(len(thresh)):
        for x in range(len(thresh[y])):
            if thresh[y][x] == 1 and is_contour_point(x, y, thresh):
                matrix[y][x] = 0

    # Поиск точки в центре которая принадлежит объекту
    koordinata = REGION // 2  # Делим без остатка
    sp = spiral(koordinata, koordinata, 3)
    x, y = next(sp)
    while matrix[y][x] == 0:
        try:
            x, y = next(sp)
        except:
            raise ('Точка не найдена')

    print(f'x={x}, y={y}')
    matrix[y][x] = 9

    # Печать матрицы
    for i in matrix:
        for j in range(len(i)):
            if i[j] == 1:
                print("\033[31m {}".format('0'), end='')
            elif i[j] == 9:
                print("\033[33m {}".format('0'), end='')
            else:
                print("\033[39m {}".format('0'), end='')
        print()


save_image()
safe_to_bd()

conn.commit()

conn.close()
