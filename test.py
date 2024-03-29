# """Программа делает скриншот, преобразует в строковый формат и сохраняет в excel файле"""
#
# from PIL import Image
# import pyautogui
# import openpyxl
# from time import sleep
#
# sleep(3)   # Задержка, чтобы сохранить тот экран, который нужен
#
# # Делаем скриншот всего экрана
# screenshot = pyautogui.screenshot()
#
# # Уменьшаем разрешение изображения до 192x108 пикселей
# resized_image = screenshot.resize((192, 108), Image.LANCZOS)
#
# resized_image.save('resized_image.png')
#
#
# # Создаем новый Excel-файл
# wb = openpyxl.Workbook()
# ws_all = wb.create_sheet('all')
# ws_color = wb.create_sheet('color')
#
#
#
# # Получаем RGB цифры каждого пикселя и записываем в соответствующий массив и Excel-файл
# for y in range(resized_image.height):
#     for x in range(resized_image.width):
#         r, g, b = resized_image.getpixel((x, y))
#         rgb_str = f"{r},{g},{b}"
#         ws_all.cell(row=y + 1, column=x + 1, value=rgb_str)
#
#         if r >= 188 and g >= 188 and b >= 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='w')   # white
#         elif r >= 188 and g >= 188 and b < 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='y')   # yellow
#         elif r >= 188 and g < 188 and b >= 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='r')   # red
#         elif r >= 188 and g < 188 and b < 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='v')   # violet
#         elif r < 188 and g >= 188 and b >= 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='l')   # light blue
#         elif r < 188 and g >= 122 and b < 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='g')   # green
#         elif r < 188 and g < 188 and b >= 188:
#             ws_color.cell(row=y + 1, column=x + 1, value='b')   # blue
#         elif r < 188 and g < 188 and (b >= 56 and b < 188):
#             ws_color.cell(row=y + 1, column=x + 1, value='e')   # grey
#         elif r < 188 and g < 188 and b < 56:
#             ws_color.cell(row=y + 1, column=x + 1, value='k')   # black
#
# # Сохраняем Excel-файл
# wb.save('pixels_colors.xlsx')
#
# # Открываем созданный Excel-файл
# wb = openpyxl.load_workbook('pixels_colors.xlsx')
#
# # Изменяем ширину столбцов в каждом листе до значения 3 (26 пикселей)
# for sheet in wb.sheetnames:
#     ws = wb[sheet]
#     for column in ws.columns:
#         ws.column_dimensions[column[0].column_letter].width = 3
#
# # Сохраняем изменения
# # wb.save('pixels_colors.xlsx')
#
# from openpyxl.styles import PatternFill
#
# # Устанавливаем цвета для закраски
# colors = {'w': 'FFFFFF', 'y': 'FFFF00', 'r': 'FF0000', 'v': '800080', 'l': 'ADD8E6', 'g': '008000', 'b': '0000FF', 'r': '808080', 'k': '000000'}
#
# # Проходим по каждой ячейке в листе ws_all и ws_color и устанавливаем соответствующий цвет
# for y in range(1, resized_image.height + 1):
#     for x in range(1, resized_image.width + 1):
#         color_code = ws_color.cell(row=y, column=x).value
#         if color_code in colors:
#             color = colors[color_code]
#             fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
#             ws_all.cell(row=y, column=x).fill = fill
#             ws_color.cell(row=y, column=x).fill = fill
#             ws_all.cell(row=y, column=x).value = ''
#
# # Сохраняем изменения
# wb.save('pixels_colors.xlsx')




import pyautogui
import cv2
from PIL import Image

# 1. Сделать скриншот изображения
# image = pyautogui.screenshot()
# image.save('screenshot.png')
#
#
# # 3. Определить границы между объектами
# img = cv2.imread('screenshot.png')
# img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# edges = cv2.Canny(img_gray, 100, 200)   # Чем меньше цифры - тем точнее контуры. Изначально было 100, 200.
#
# cv2.imshow("Edges", edges)
# cv2.waitKey(0)
# cv2.destroyAllWindows()



# Расчёт нейронной сети:
#
# import math
#
# def sigmoid(x):
#     return 1 / (1 + math.exp(-x))
#
#
# i1 = 1
# i2 = 0
# w1 = 1   # 0.45
# w2 = 1   # 0.78
# w3 = 1   # -0.12
# w4 = 1   # 0.13
# w5 = 1   # 1.5
# w6 = 1   # -2.3
#
# H1input = i1 * w1 + i2 * w3   # 0.45
# H1output = sigmoid(H1input)   # 0.61
#
# H2input = i1*w2+i2*w4   # 0.78
# H2output = sigmoid(H2input)   # 0.69
#
# O1input = H1output*w5+H2output*w6   # -0.672
# O1output = sigmoid(O1input)   # 0.33
#
# O1ideal = 1
# iteraciya = 1
#
# Error = ((O1ideal-O1output)*(O1ideal-O1output))/iteraciya   # 0.45
#
# print(f'O1output: {O1output}    Error: {Error}')


import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('Li_db_v1_4.db')
cursor = conn.cursor()

# Строка для сравнения
name_look = 'abfefafebeefaeef'

# Перебор символов и выполнение запроса для каждого символа
for i, char in enumerate(name_look):
    print(f'Рассматривается i = {i} и char = {char}')
    cursor.execute("UPDATE tochki SET work = work + 1 WHERE SUBSTR(name, ?, 1) = ? AND type = 'mozg'", (i + 1, char))
    # cursor.execute("SELECT ID FROM tochki WHERE SUBSTR(name, ?, 1) = ?", (i+1, char))
    # rows = cursor.fetchall()
    # for row in rows:
    #     print(row)
    poisk_work = cursor.execute("SELECT ID FROM tochki WHERE SUBSTR(name, ?, 1) = ? AND type = 'mozg'", (i+1, char))
    for poisk_work1 in poisk_work:
        print(f'Найден следующий ID: {poisk_work1}')

# Закрываем соединение с базой данных
conn.close()
