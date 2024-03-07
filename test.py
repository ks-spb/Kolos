"""Программа делает скриншот, преобразует в строковый формат и сохраняет в excel файле"""

from PIL import ImageGrab
import numpy as np
import openpyxl
import pandas as pd

# Делаем скриншот экрана размером 100x100 пикселей
screenshot = ImageGrab.grab(bbox=(0, 0, 100, 100))

# Преобразуем изображение в массив numpy
screenshotarray = np.array(screenshot)

# Создаем новый Excel файл
wb = openpyxl.Workbook()
ws = wb.active

# Создаем словарь для каждого цвета радуги
rainbowcolors = {"красный": [], "серый": [], "желтый": [], "зелёный": [], "голубой": [], "синий": [],
    "фиолетовый": [], "белый": [], "черный": []}


list_white = np.where((screenshotarray[:, :, 0] >= 188) & (screenshotarray[:, :, 1] >= 188) & (screenshotarray[:, :, 2] >= 188), 999, 0)
df = pd.DataFrame(list_white)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_white.xlsx', index=False, header=False)

list_yellow = np.where((screenshotarray[:, :, 0] >= 188) & (screenshotarray[:, :, 1] >= 188) & (screenshotarray[:, :, 2] < 188), 999, 0)
df = pd.DataFrame(list_yellow)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_yellow.xlsx', index=False, header=False)

list_red = np.where((screenshotarray[:, :, 0] >= 188) & (screenshotarray[:, :, 1] < 188) & (screenshotarray[:, :, 2] >= 188), 999, 0)
df = pd.DataFrame(list_red)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_red.xlsx', index=False, header=False)

list_violet = np.where((screenshotarray[:, :, 0] >= 188) & (screenshotarray[:, :, 1] < 188) & (screenshotarray[:, :, 2] < 188), 999, 0)
df = pd.DataFrame(list_violet)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_violet.xlsx', index=False, header=False)

list_light_blue = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] >= 188) & (screenshotarray[:, :, 2] >= 188), 999, 0)
df = pd.DataFrame(list_light_blue)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_light_blue.xlsx', index=False, header=False)

list_green = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] >= 188) & (screenshotarray[:, :, 2] < 188), 999, 0)
df = pd.DataFrame(list_green)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_green.xlsx', index=False, header=False)

list_blue = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] < 188) & (screenshotarray[:, :, 2] >= 188), 999, 0)
df = pd.DataFrame(list_blue)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_blue.xlsx', index=False, header=False)

list_gray = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] < 188) & ((screenshotarray[:, :, 2] >= 56) & (screenshotarray[:, :, 2] < 188)), 999, 0)
df = pd.DataFrame(list_gray)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_gray.xlsx', index=False, header=False)

list_black = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] < 188) & (screenshotarray[:, :, 2] < 56), 999, 0)
df = pd.DataFrame(list_black)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_black.xlsx', index=False, header=False)

wb.save("screenshot.xlsx")
screenshot.save("screenshot.png")

