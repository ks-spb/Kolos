"""
Сохранение изображения кнопки/иконки (элемента)

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

REGION = 97  # Сторона квадрата получаемого изображения с экрана для поиска в нем элемента
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений

def save_image(x_point :int, y_point :int) -> str:
    """ Сохранение изображения кнопки/иконки (элемента)

    Функция принимает в качестве аргументов координаты точки на экране.
    Предполагается, что эта точка расположена на элементе, изображение которого нужно сохранить.
    Точка принимается как цент квадрата. Внутри него будет искаться изображение элемента.
    Возвращает имя нового изображения.

    """

    # Вычисляем координаты квадрата для скриншота
    x_reg = x_point - REGION // 2
    y_reg = y_point - REGION // 2

    # Координаты точки на новом регионе
    x_point -= x_reg
    y_point -= y_reg

    # Делаем скриншот
    image = pyautogui.screenshot(region=(x_reg, y_reg, REGION-1, REGION-1))  # x, y, x+n, y+n (с верхнего левого угла)
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # apply binary thresholding
    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 40, 255, cv2.THRESH_BINARY)
    # cv2.imwrite("in_memory_to_disk.png", thresh)

    # Нахождение контуров
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ищем контур, которому принадлежит точка
    for c in contours:
        x,y,w,h = cv2.boundingRect(c)
        if x_point >= x and x_point <= x+w and y_point >= y and y_point <= y+h:
            # Координаты точки принадлежат прямоугольнику описанному вокруг контура
            break
    else:
        # Проверены все контуры, точка непринадлежит ни одному
        raise Exception('Элемент не найден')

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    return f'{filename}.png'
