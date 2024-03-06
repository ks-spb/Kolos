"""Программа делает скриншот, преобразует в строковый формат и сохраняет в excel файле"""


# from PIL import ImageGrab
# import numpy as np
# import openpyxl
#
# # Делаем скриншот экрана размером 100x100 пикселей
# screenshot = ImageGrab.grab(bbox=(0, 0, 100, 100))
#
# # Преобразуем изображение в массив numpy
# screenshot_array = np.array(screenshot)
#
# # Создаем новый Excel файл
# wb = openpyxl.Workbook()
# ws = wb.active
#
# # Преобразуем массив RGB значений в строковый формат и добавляем в Excel файл
# for row in screenshot_array:
#     row_values = ['{}, {}, {}'.format(pixel[0], pixel[1], pixel[2]) for pixel in row]
#     ws.append(row_values)
#
# # Сохраняем Excel файл
# wb.save("screenshot.xlsx")
# screenshot.save("screenshot.png")

# from PIL import ImageGrab
# import numpy as np
# import openpyxl
#
# # Делаем скриншот экрана размером 100x100 пикселей
# screenshot = ImageGrab.grab(bbox=(0, 0, 100, 100))
#
# # Преобразуем изображение в массив numpy
# screenshotarray = np.array(screenshot)
#
# # Создаем новый Excel файл
# wb = openpyxl.Workbook()
# ws = wb.active
#
# # Создаем списки для каждого цвета радуги
# rainbowcolors = {"красный": [], "оранжевый": [], "желтый": [], "зелёный": [], "голубой": [], "синий": [],
#                  "фиолетовый": []}
#
# # Проходим по каждому пикселю и добавляем его в соответствующий список цвета
# for row in screenshotarray:
#     for pixel in row:
#         if pixel[0] >= 200 and pixel[1] < 100 and pixel[2] < 100:
#             rainbowcolors["красный"].append(pixel)
#         elif pixel[0] >= 200 and pixel[1] >= 100 and pixel[2] < 100:
#             rainbowcolors["оранжевый"].append(pixel)
#         elif pixel[0] >= 200 and pixel[1] >= 200 and pixel[2] < 100:
#             rainbowcolors["желтый"].append(pixel)
#         elif pixel[0] < 100 and pixel[1] >= 200 and pixel[2] < 100:
#             rainbowcolors["зелёный"].append(pixel)
#         elif pixel[0] < 100 and pixel[1] >= 200 and pixel[2] >= 200:
#             rainbowcolors["голубой"].append(pixel)
#         elif pixel[0] < 100 and pixel[1] < 100 and pixel[2] >= 200:
#             rainbowcolors["синий"].append(pixel)
#         elif pixel[0] >= 100 and pixel[1] < 100 and pixel[2] >= 200:
#             rainbowcolors["фиолетовый"].append(pixel)
#
# # Создаем Excel файлы для каждого цвета
# for color, pixels in rainbowcolors.items():
#     wb = openpyxl.Workbook()
#     ws = wb.active
#     for pixel in pixels:
#         ws.append(['{}, {}, {}'.format(pixel[0], pixel[1], pixel[2])])
#     wb.save(f"screenshot{color}.xlsx")


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

list_black = np.where((screenshotarray[:, :, 0] < 188) & (screenshotarray[:, :, 1] < 188) & (screenshotarray[:, :, 2] < 188), 999, 0)
df = pd.DataFrame(list_black)  # Создание DataFrame из списка
# Сохранение DataFrame в Excel файл
df.to_excel('list_black.xlsx', index=False, header=False)

# print("list_white", list_white)
# print(list_white)
# print("list_yellow", list_yellow)
# print(list_yellow)
# print("list_red", list_red)
# print(list_red)
# print("list_violet", list_violet)
# print(list_violet)
# print("list_light_blue", list_light_blue)
# print(list_light_blue)
# print("list_green", list_green)
# print(list_green)
# print("list_blue", list_blue)
# print(list_blue)
# print("list_gray", list_gray)
# print(list_gray)

wb.save("screenshot.xlsx")
screenshot.save("screenshot.png")

