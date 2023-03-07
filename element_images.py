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
FIRST_REGION = 96  # Сторона квадрата, в котором ищутся сохраненные элементы
REGION = 48  # Сторона квадрата с сохраняемым элементом

BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений

REGION_FOR_SEARCH = 96  # Сторона квадрата в котором производится первоначальный поиск элемента
# Где искать элемент: full - по всему экрану, region - в квадрате с заданными координатами, all - везде
WHERE_TO_LOOK = 'full'


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
    """ Сохранение изображения кнопки/иконки (элемента) если он еще не сохранен

    Функция принимает в качестве аргументов координаты точки на экране.
    Предполагается, что эта точка расположена на элементе, изображение которого нужно сохранить или найти.
    Точка принимается как цент квадрата со стороной FIRST_REGION внутри которого должен находиться
    элемент (кнопка, иконка...). Проверяются сохраненные элементы. Если такого нет квадрат обрезается
    до размера стороны REGION и сохраняется. Если есть, возвращается его имя.
    Возвращает имя нового или существующего изображения.

    """

    threshold = 0.8 # Порог
    method = cv2.TM_CCOEFF_NORMED  # Метод расчёта корреляции между изображениями

    # Вычисляем координаты квадрата для скриншота
    x_reg = x_point - FIRST_REGION // 2
    y_reg = y_point - FIRST_REGION // 2

    # Делаем скриншот нужного квадрата
    image = screenshot(x_reg, y_reg, FIRST_REGION-1)

    # Перевод изображения в оттенки серого
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Перебор сохраненных элементов, был ли ранее такой сохранен
    for name in os.listdir(PATH):
        template = cv2.imread(f'{PATH}/{name}', 0)
        # Операция сопоставления
        res = cv2.matchTemplate(gray_img, template, method)
        # Ищем координаты совпадающего местоположения в массиве numpy
        loc = np.where(res >= threshold)
        if any(loc[-1]):
            return name

    # Если выбранный элемент ранее не был сохранен, сохраним его
    # Обрезаем квадрат
    a = (FIRST_REGION - REGION) // 2
    image = image[a: a + REGION, a: a + REGION]

    # Координаты точки на новом регионе
    x_point = x_point - x_reg - a
    y_point = y_point - y_reg - a

    # cv2.imshow('', image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()
    # Перевод изображения в оттенки серого
    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # apply binary thresholding
    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(gray_img, 100, 255, cv2.THRESH_BINARY)
    # cv2.imwrite("in_memory_to_disk.png", thresh)

    # Нахождение контуров
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ищем контур, которому принадлежит np.array(image)точка
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if x_point >= x and x_point <= x+w and y_point >= y and y_point <= y+h:
            # Координаты точки принадлежат прямоугольнику описанному вокруг контура
            break
    else:
        # Проверены все контуры, точка не принадлежит ни одному
        # Выбираем весь квадрат
        x = y = 0
        w = h = REGION

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    # print(ROI.set_printoptions(threshold=ROI.nan))

    return f'{filename}.png'



def pattern_search(name_template: str, x_point: int = 0, y_point: int = 0) -> tuple:
    """ Подтверждение присутствия нужной кнопки в указанных координатах или поиск ее на экране

    Константа WHERE_TO_LOOK = 'full' задает режим поиска:
    full - только по всему экрану, region - только в квадрате с заданными координатами и размером
    стороны в константе REGION_FOR_SEARCH,
    all - если не найдено в заданном квадрате - то искать по всему экрану.
    Принимает в качестве первого аргумента имя шаблона (изображения кнопки или ее части),
    которое ищет по пути в константе PATH. Второй и третий аргументы - координаты на экране
    где должна присутствовать кнопка.
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

    # Сохранить ширину в переменной w и высоту в переменной h шаблона
    w, h = template.shape

    # Где искать элемент
    if WHERE_TO_LOOK != 'full':

        # Вычисляем координаты квадрата для скриншота
        x_reg = x_point - REGION_FOR_SEARCH // 2
        y_reg = y_point - REGION_FOR_SEARCH // 2

        # Делаем скриншот нужного квадрата
        image = screenshot(x_reg, y_reg, REGION_FOR_SEARCH - 1)

        # Перевод изображения в оттенки серого
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Операция сопоставления
        res = cv2.matchTemplate(gray_img, template, method)

        # Ищем координаты совпадающего местоположения в массиве numpy
        loc = np.where(res >= threshold)

        if any(loc[-1]):
            # Элемент присутствует в этом месте, подтверждаем координаты
            return (x_point, y_point)
        elif WHERE_TO_LOOK != 'all':
            # Элемент не найден в заданном месте, а поиск по всему экрану не включен
            raise Exception('Элемент не найден в указанной области.')

        # Если поиск шаблона в заданных координатах не принес результата any(loc[-1] будет пустым.
        # Ищем на всем экране если это разрешено

    if WHERE_TO_LOOK == 'full' or WHERE_TO_LOOK == 'all':
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
            # Вернуть координаты центра нового положения элемента
            return (xy[0] + w / 2, xy[1] + h / 2)

        else:
            # Заданный шаблон на экране не найден
            raise Exception('Указанный элемент на экране не найден.')
