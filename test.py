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
image = pyautogui.screenshot()
image.save('screenshot.png')


# 3. Определить границы между объектами
img = cv2.imread('screenshot.png')
img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(img_gray, 100, 200)   # Чем меньше цифры - тем точнее контуры. Изначально было 100, 200.

cv2.imshow("Edges", edges)
cv2.waitKey(0)
cv2.destroyAllWindows()
