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


# Настройки
REGION = 48  # Сторона квадрата получаемого изображения с экрана для поиска в нем элемента
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений
REGION_FOR_SEARCH = 96  # Сторона квадрата в котором производится первоначальный поиск элемента
ADVANCED_SEARCH = True  # Нужно ли выполнить поиск элемента на всем экране, еси в указанных координатах его нет


def screenshot(x_reg: int = 0, y_reg: int = 0, region: int = 0):
    """ Скриншот заданного квадрата или всего экрана

    В качестве аргументов принимает координаты верхней левой точки квадрата и его стороны.
    Если сторона на задана (равна 0) то делает скриншот всего экрана

    """
    if region:
        image = pyautogui.screenshot(region=(x_reg, y_reg, region, region))  # x, y, x+n, y+n (с верхнего левого угла)
    else:
        image = pyautogui.screenshot()
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


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

    # Делаем скриншот нужного квадрата
    image = screenshot(x_reg, y_reg, REGION-1)
    # image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # apply binary thresholding
    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)
    # cv2.imwrite("in_memory_to_disk.png", thresh)

    # Нахождение контуров
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ищем контур, которому принадлежит np.array(image)точка
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

    # print(ROI.set_printoptions(threshold=ROI.nan))

    return f'{filename}.png'



def pattern_search(name_template: str, x_point: int = 0, y_point: int = 0) -> tuple:
    """ Подтверждение присутствия нужной кнопки в указанных координатах или поиск ее на экране

    Принимает в качестве первого аргумента имя шаблона (изображения кнопки или ее части),
    которое ищет по пути в константе PATH. Второй и третий аргументы - координаты на экране
    где должна присутствовать кнопка. Если ее там нет, производится поиск по всему экрану.
    В случае, если кнопка не найдена, поднимается исключение "Элемент не найден". Иначе
    возвращаются координаты (x, y в tuple) куда нужно совершить клик.

    """

    threshold = 0.8 # Порог
    method = cv2.TM_CCOEFF_NORMED  # Метод расчёта корреляции между изображениями

    # Получение шаблона
    try:
        template = cv2.imread(f'{PATH}/{name_template}', 0)
    except:
        raise FileNotFoundError('Шаблон с таким именем не найден')

    # Вычисляем координаты квадрата для скриншота
    x_reg = x_point - REGION_FOR_SEARCH // 2
    y_reg = y_point - REGION_FOR_SEARCH // 2

    # Делаем скриншот нужного квадрата
    image = screenshot(x_reg, y_reg, REGION_FOR_SEARCH - 1)

    # Перевод изображения в оттенки серого
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Сохранить ширину в переменной w и высоту в переменной h шаблона
    w, h = template.shape

    # Операция сопоставления
    res = cv2.matchTemplate(gray_img, template, method)

    # Ищем координаты совпадающего местоположения в массиве numpy
    loc = np.where(res >= threshold)

    if not any(loc[-1]):
        # Поиск шаблона в заданных координатах не принес результата
        # Ищем на всем экране если это разрешено константой ADVANCED_SEARCH

        if ADVANCED_SEARCH:
            # Поиск элемента на всем экране

            # Делаем скриншот экрана
            image = screenshot()

            # Перевод изображения в оттенки серого
            gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Операция сопоставления
            res = cv2.matchTemplate(gray_img, template, method)

            # Ищем координаты совпадающего местоположения в массиве numpy
            loc = np.where(res >= threshold)
            xy = list(zip(*loc[::-1]))[-1]

            # Проверка, найден ли шаблон на всем экране
            if xy:
                # # Нарисуйте прямоугольник вокруг совпадающей области
                # pt = xy
                # d = cv2.rectangle(image, pt, (pt[0] + w, pt[1] + h), (0, 255, 255), 2)
                #
                # # Отобразить окончательное совпадающее изображение шаблона
                # cv2.imshow('Detected', d)
                # cv2.waitKey(0)


                # Вернуть координаты середины нового положения элемента
                print('Элемент найден не в указанном месте.')
                return (xy[0] + w / 2, xy[1] + h / 2)

            else:
                # Заданный шаблон на экране не найден
                raise Exception('Указанный элемент на экране не найден.')

        else:
            # Расширенный поиск отключен, возвращаем исключение
            raise Exception('Указанного элемента нет в заданном месте экрана.'
                            'Поиск по всему экрану отключен.')
    else:
        print('Элемент найден в указанном месте.')
    return (x_point, y_point)