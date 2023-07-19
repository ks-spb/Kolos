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


def save_image():


    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = f'{"_".join([BASENAME, suffix])}.png'

    screenshot = pyautogui.screenshot()
    # Сохраняем скриншот с уменьшенным качеством
    screenshot.save(filename, "JPEG", optimize=True, quality=quality)

    # cv2.imwrite(os.path.join(PATH, filename))

    return filename


def preobrazovanie_img(filename):
    """
    Функция открывает файл с сохранённым изображением, преобразовывает в ч/б и сохраняет в csv
    """

    img = np.asarray(Image.open(os.path.join(filename)))

    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

    # сохранение scv файла в цвете в csv:
    # np.savetxt(f"{PATH}/{filename}.csv", img.reshape(REGION, -1), delimiter=",", fmt="%s", header=str(img.shape))

    np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл
    # print('thresh:\n', thresh)


preobrazovanie_img(save_image())
