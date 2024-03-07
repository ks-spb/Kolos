"""Программа делает скриншот, преобразует в строковый формат и сохраняет в excel файле"""

from PIL import Image
import pyautogui
import openpyxl
from time import sleep

sleep(3)   # Задержка, чтобы сохранить тот экран, который нужен

# Делаем скриншот всего экрана
screenshot = pyautogui.screenshot()

# Уменьшаем разрешение изображения до 192x108 пикселей
resized_image = screenshot.resize((192, 108), Image.LANCZOS)

# Создаем новые массивы для цветов white, yellow и red
white_pixels = []
yellow_pixels = []
red_pixels = []
violet_pixels = []
light_blue_pixels = []
green_pixels = []
blue_pixels = []
gray_pixels = []
black_pixels = []


# Создаем новый Excel-файл
wb = openpyxl.Workbook()
ws_white = wb.create_sheet('white')
ws_yellow = wb.create_sheet('yellow')
ws_red = wb.create_sheet('red')
ws_violet = wb.create_sheet('violet')
ws_light_blue = wb.create_sheet('light_blue')
ws_green = wb.create_sheet('green')
ws_blue = wb.create_sheet('blue')
ws_gray = wb.create_sheet('gray')
ws_black = wb.create_sheet('black')


# Получаем RGB цифры каждого пикселя и записываем в соответствующий массив и Excel-файл
for y in range(resized_image.height):
    for x in range(resized_image.width):
        r, g, b = resized_image.getpixel((x, y))
        rgb_str = f"{r},{g},{b}"

        if r >= 188 and g >= 188 and b >= 188:
            ws_white.cell(row=y + 1, column=x + 1, value=999)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r >= 188 and g >= 188 and b < 188:
            # yellow_pixels.append(999)
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=999)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r >= 188 and g < 188 and b >= 188:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=999)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r >= 188 and g < 188 and b < 188:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=999)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r < 188 and g >= 188 and b >= 188:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=999)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r < 188 and g >= 188 and b < 188:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=999)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r < 188 and g < 188 and b >= 188:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=999)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r < 188 and g < 188 and (b >= 56 and b < 188):
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=999)
            ws_black.cell(row=y + 1, column=x + 1, value=0)
        elif r < 188 and g < 188 and b < 56:
            ws_white.cell(row=y + 1, column=x + 1, value=0)
            ws_yellow.cell(row=y + 1, column=x + 1, value=0)
            ws_red.cell(row=y + 1, column=x + 1, value=0)
            ws_violet.cell(row=y + 1, column=x + 1, value=0)
            ws_light_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_green.cell(row=y + 1, column=x + 1, value=0)
            ws_blue.cell(row=y + 1, column=x + 1, value=0)
            ws_gray.cell(row=y + 1, column=x + 1, value=0)
            ws_black.cell(row=y + 1, column=x + 1, value=999)

# Сохраняем Excel-файл
wb.save('pixels_colors.xlsx')



