"""
Модуль выполняет скриншот изображения и его преобразование в точки
"""

"""
Сохранение изображения кнопки/иконки (элемента) и подтверждение его присутствия

$ sudo apt-get install scrot
$ sudo apt-get install python-tk python-dev
$ sudo apt-get install python3-tk python3-dev
$ workon your_virtualenv
$ pip install pillow imutils
$ pip install python3_xlib python-xlib
$ pip install pyautogui
https://pyimagesearch.com/2018/01/01/taking-screenshots-with-opencv-and-python/

"""

import os, sys
import datetime
import numpy as np
import pyautogui
import cv2
from PIL import Image


# Настройки
FIRST_REGION = 96  # Сторона квадрата, в котором ищутся сохраненные элементы
REGION = 20  # Сторона квадрата с сохраняемым элементом

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


# def image_to(filename_):
#
#     # прочитать изображение
#     img = cv2.imread(filename_)
#
#     image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
#
#     # преобразовать изображение в формат оттенков серого
#     img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#
#     # apply binary thresholding
#     # Применение бинарного порога к изображению
#     ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)
#
#     print(thresh)
#     print(ret)
#
#     np.savetxt(f"{PATH}/{filename_}.csv", thresh, delimiter=" ,", fmt=" %.0f ")


def save_image():
    """ Сохранение изображения кнопки/иконки (элемента) если он еще не сохранен

    Функция принимает в качестве аргументов координаты точки на экране.
    Предполагается, что эта точка расположена на элементе, изображение которого нужно сохранить или найти.
    Точка принимается как центр квадрата со стороной FIRST_REGION внутри которого должен находиться
    элемент (кнопка, иконка...). Проверяются сохраненные элементы. Если такого нет квадрат обрезается
    до размера стороны REGION и сохраняется. Если есть, возвращается его имя.
    Возвращает имя нового или существующего изображения.
    https://myrusakov.ru/current-mouse-position-python.html

    """

    x_pos, y_pos = pyautogui.position()
    print('Позиция мыши следующая: ', x_pos, y_pos)

    # Делаем скриншот нужного квадрата
    image = screenshot(x_pos-REGION/2, y_pos-REGION/2, FIRST_REGION-1)

    x = y = 0
    w = h = REGION

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    preobrazovanie_img(filename)

    return f'{filename}.png'


def preobrazovanie_img(filename):
    img = np.asarray(Image.open(f'{PATH}/{filename}.png'))

    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

    """
    для сохранения scv файла в цвете - нужно раскомментировать эти 2 строчки: 
    # np.save("nxx.npy", img)
    # np.savetxt(f"{PATH}/{filename}.csv", img.reshape(REGION, -1), delimiter=",", fmt="%s", header=str(img.shape))
    """

    # np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")




save_image()
