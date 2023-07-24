# Функция создаёт скриншот, уменьшает качество, ищет схожее состояние, если не находит - записывает новое

import pyautogui
import os, sys
import numpy as np
import cv2
import time
from PIL import Image
import datetime

# time.sleep(2)
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


# Открытие изображение
image = screenshot()
# image = 'C:\python\Kolos\elements_img\elem_230721_130631.png'
# image = cv2.imread(image)
image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
img = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)[1] # ensure binary

# Делаем фон черным.
# Строим гистограмму изображения
hist = cv2.calcHist([img], [0], None, [256], [0, 256])
# Определяем значение пикселя, которое соответствует наибольшему пику, это фон
background_color = np.argmax(hist)

if background_color != 0:
    # Инвертируем значения пикселей в изображении, чтобы фон был черным - 0
    img = cv2.bitwise_not(img)

num_labels, labels_im = cv2.connectedComponents(img)
print(img)


# Создаём словарь, в котором будем хранить координаты пикселей, принадлежащих каждой компоненте связности
components = {}
quantity = 0  # Количество элементов
for label in range(1, num_labels):
    # Получаем координаты пикселей, которые принадлежат к текущей компоненте связности
    coords = np.where(labels_im == label)
    if len(coords[0]) > 5:
        # Если размер компоненты устраивает
        # Преобразуем координаты в список кортежей и добавляем в словарь
        components[label] = list(zip(coords[0], coords[1]))
        quantity += 1

print(components)
print(quantity)