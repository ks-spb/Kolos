# Функция создаёт скриншот, уменьшает качество, ищет схожее состояние, если не находит - записывает новое

import pyautogui
import os, sys
import numpy as np
import cv2
from PIL import Image
import datetime

# Задаем уровень качества (чем меньше число, тем ниже качество)
quality = 1  # Можете выбрать значение от 1 до 95

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

