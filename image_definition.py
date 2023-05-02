"""
Модуль выполняет скриншот изображения и его преобразование в точки
"""

import os, sys
import datetime
import numpy as np
import pyautogui
import cv2
from PIL import Image
import sqlite3
import time


conn = sqlite3.connect('Li_db_v1_4.db')
cursor = conn.cursor()
# Настройки
# REGION должен быть больше, чем 17х17, чтобы можно было один раз сделать скриншот и работать с квадратом 17х17.
# 21 - это 17 + 4 слоя для возможности перемещения.
REGION = 21  # Сторона квадрата с сохраняемым элементом. Ставить нечетным!
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений
thresh = []   # Список, в котором будет храниться обработанное изображение
posl_tg = 1
posl_koord = 0

def stiranie_pamyati():
    # Удаление лишних строчек в таблицах БД
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM glaz WHERE ID > 1")
    cursor.execute("DELETE FROM svyazi_glaz WHERE ID > 1")


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
    """
    Функция определяет положение курсора мыши, делает скриншот квадрата с заданными размерами и сохраняет файл с img
    """
    x_pos, y_pos = pyautogui.position()
    # print('Позиция мыши следующая: ', x_pos, y_pos)

    # Делаем скриншот нужного квадрата, где центр - координаты мыши
    # image = screenshot(0.5+x_pos-REGION/2, 0.5+y_pos-REGION/2, REGION)

    # скриншот целого экрана
    image = screenshot()

    x = y = 0
    # w = h = REGION
    h = 30
    w = 30   # в csv-файле показывается 600 цифр, в том числе пробелы и запятые

    # Сохраняем изображение найденного элемента
    ROI = image[y:y+h, x:x+w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = "_".join([BASENAME, suffix])  # e.g. 'mylogfile_120508_171442'
    cv2.imwrite(f'{PATH}/{filename}.png', ROI)

    preobrazovanie_img(filename)

def preobrazovanie_img(filename):
    """
    Функция открывает файл с сохранённым изображением, преобразовывает в ч/б и сохраняет в csv
    """
    global thresh

    img = np.asarray(Image.open(f'{PATH}/{filename}.png'))

    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

    # сохранение scv файла в цвете в csv:
    # np.savetxt(f"{PATH}/{filename}.csv", img.reshape(REGION, -1), delimiter=",", fmt="%s", header=str(img.shape))

    np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл
    # print('thresh:\n', thresh)



def sozdat_new_tochky(name, work, type, func, porog, signal, puls, rod1, rod2):
    max_ID = cursor.execute("SELECT MAX(ID) FROM glaz").fetchone()
    new_id = max_ID[0] + 1
    cursor.execute("INSERT INTO glaz VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id, name, work, type, func, porog, signal, puls, rod1, rod2, name))
    return new_id


def sozdat_svyaz(id_start: int = 0, id_finish: int = 0, koord_start: int = 0, koord_finish: int = 0):
    max_ID_svyazi = tuple(cursor.execute("SELECT MAX(ID) FROM svyazi_glaz"))
    for max_ID_svyazi1 in max_ID_svyazi:
        old_id_svyazi = max_ID_svyazi1[0]
        new_id_svyazi = old_id_svyazi + 1
    cursor.execute("INSERT INTO svyazi_glaz VALUES (?, ?, ?, ?, ?, ?)", (new_id_svyazi, id_start, id_finish, 1,
                                                                         koord_start, koord_finish))


def fill(matrix, x, y):
    """ Обход точек и формирование списка смещения каждой точки от заданной """
    global posl_koord
    global posl_tg
    start_x, start_y = x, y
    out = []
    stack = [(x, y)]
    while stack:
        x, y = stack.pop()
        if matrix[x][y] == 1:
            matrix[x][y] = 2
            print(f"В путь добавлена точка с координатами: {y}, {x}. Это смещение: {y - start_y}, {x - start_x}")
            out.append((x - start_x, y - start_y))
            # поиск имеется ли точка в БД, соответствующая этому смещению
            name_smesheniya = str(x - start_x) + '_' + str(y - start_y)
            poisk_smesheniya = tuple(cursor.execute("SELECT name FROM glaz WHERE name = ?", (name_smesheniya,)))
            sozdat_svyaz(0, 0, posl_koord, name_smesheniya)
            posl_koord = name_smesheniya
            if not poisk_smesheniya:
                # если нет - создать
                sozdat_new_tochky(name_smesheniya, 0, 'sdvig', 'zazech_sosedey', 1, 0, 0, posl_koord, 0)
                new_smeshenie = name_smesheniya
            else:
                for poisk_smesheniya1 in poisk_smesheniya:
                    for poisk_smesheniya2 in poisk_smesheniya1:
                        new_smeshenie = poisk_smesheniya2
            # найти связующее tg м/у posl_tg и точкой сдвига
            poisk_svyazyushei_tg_s_new_smeshenie = tuple(cursor.execute(
                "SELECT ID FROM glaz WHERE rod1 = ? AND rod2 = ?", (posl_tg, new_smeshenie)))
            if not poisk_svyazyushei_tg_s_new_smeshenie:
                new_tg = sozdat_new_tochky('time_g', 0, 'time', 'zazech_sosedey', 1, 0, 0, posl_tg, new_smeshenie)
                # sozdat_svyaz(0, new_tg, new_smeshenie, 0)
                sozdat_svyaz(posl_tg, new_tg, 0, 0)
                posl_tg = new_tg
            else:
                for poisk_svyazyushei_tg_s_new_smeshenie1 in poisk_svyazyushei_tg_s_new_smeshenie:
                    for poisk_svyazyushei_tg_s_new_smeshenie2 in poisk_svyazyushei_tg_s_new_smeshenie1:
                        # sozdat_svyaz(0, poisk_svyazyushei_tg_s_new_smeshenie2, new_smeshenie, 0)
                        posl_tg = poisk_svyazyushei_tg_s_new_smeshenie2
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == dy == 0:
                        continue
                    new_x = x + dx
                    new_y = y + dy
                    if 0 <= new_x < matrix.shape[0] and 0 <= new_y < matrix.shape[1]:
                        stack.append((new_x, new_y))
    return out



def save_to_bd():
    # Функция сохраняет изображение в таблицу glaz, начиная от центральной точки, которая = REGION/2+0.5,
    # но перед этим определяет, что находится в центре - если это фон - то ищется точка объекта по спирали
    global thresh
    global REGION
    global posl_tg
    global posl_koord

    thresh[thresh == 255] = 1  # Меняем в массиве 255 на 1

    # Определяем, что является чернилами
    ink = 1 if sum(np.sum(i == 1) for i in thresh) < (len(thresh) * len(thresh[0])) // 2 else 0

    # Меняем чернила на 1, а фон на 0
    if not ink:
        mask = thresh ^ 1
        thresh = mask.astype(np.uint8)


    filename = "Preobrazovanniy"

    np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")

    """
    Далее разбор массива thresh, который пройдётся по точкам и запишет уникальный объект в БД.
    Имеются точки сетки. Каждой координате (x,y) соответствует своя точка сетки, но они не записываются в БД.
    Имеются внутренние точки таблицы (glaz), описывающие смещение относительно начальной точки (0, 0): (0, 0), (0, 1), 
    (2,2) и т.п.
    Имеются внутренние временные точки (tg).
    1. Перебираем лист сохранённого изображения последовательно (слева направо, сверху вниз).
    2. Когда находим 1 - проверяем записана ли эта точка в таблицу svyzi_glaz в столбце koord_finish:
     2.1. Если нет - это точка (0, 0):
        2.1.1. Присвоить posl_tg = 0, 0
        2.1.2. Создать связь м/у координатой и (0, 0), присвоить координате posl_koord = (х, y)
        2.1.2. Запустить алгоритм окрашивания
        2.1.3. Каждый раз, когда будет находиться (1) перекрашивать в 2
        2.1.4. Найти соответствующую этому смещению точку в БД, если нет - создать
        2.1.5. Найти смежную (tg) между posl_tg и текущей точкой смещения
            2.1.5.1. Если нет - создать
            2.1.5.2. Если есть - присвоить ей posl_tg
        2.1.6. Создать связь м/у предыдущей координатой и текущей, присвоить текущей posl_koord
        2.1.7. Создать связь между текущей координатой и tg    
    2.2. Если есть - эта точка уже обработана - перейти дальше
    """
    posl_tg = 0
    # Перебор строк матрицы
    for i in range(len(thresh)):
        # Перебор элементов в строке
        for j in range(len(thresh[i])):
            if thresh[i][j] == 1:
                # print(f"Координаты: (y = {i}, x = {j})")
                name_tochki = str(j) + ', ' + str(i)
                print(f"Имя точки следующее: {name_tochki}")
                # если нет записи в столбце koord_finish - это точка start
                poisk_svyazi = tuple(cursor.execute("SELECT ID FROM svyazi_glaz WHERE koord_finish = ?",
                                                    (name_tochki,)))
                if not poisk_svyazi:
                    # значит эта точка (0, 0)
                    # присвоить posl_tg - начальная точка
                    posl_tg = 1
                    sozdat_svyaz(0, 1, name_tochki, 0)
                    posl_koord = name_tochki
                    fill(thresh, i, j)



stiranie_pamyati()
save_image()
save_to_bd()

conn.commit()

conn.close()
