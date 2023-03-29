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
REGION = 301  # Сторона квадрата с сохраняемым элементом. Ставить нечетным!
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений


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


def save_image():
    """
    Функция определяет положение курсора мыши, делает скриншот квадрата с заданными размерами и сохраняет файл с img
    """
    x_pos, y_pos = pyautogui.position()
    print('Позиция мыши следующая: ', x_pos, y_pos)

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


def preobrazovanie_img(filename):
    """
    Функция открывает файл с сохранённым изображением, преобразовывает в ч/б и сохраняет в csv
    """
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


# def safe_to_bd(img):
    # Функция сохраняет изображение в таблицу glaz, начиная от центральной точки, которая = REGION/2+0.5

    # TO DO определить какого цвета в изображении больше
    # Поиск цвета, который представлен больше всего - это фон, точки не будут зажигаться.
    # black = img.count(0)
    # white = img.count(255)
    #
    # print("black: ", black, "white", white)  # 3


save_image()

conn.commit()

conn.close()
