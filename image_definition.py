"""
Модуль выполняет скриншот изображения и его преобразование в точки
"""

import os, sys
import datetime
import numpy as np
import pyautogui
import cv2
from PIL import Image
from db import Database
from pynput import keyboard
import hashlib

from screen import screen


# import sqlite3
# conn = sqlite3.connect('Li_db_v1_4.db')
# cursor = conn.cursor()

# Настройки
# REGION должен быть больше, чем 17х17, чтобы можно было один раз сделать скриншот и работать с квадратом 17х17.
# 21 - это 17 + 4 слоя для возможности перемещения.
REGION = 30  # Сторона квадрата с сохраняемым элементом. Ставить нечетным!
BASENAME = "elem"  # Префикс для имени файла при сохранении изображения элемента
PATH = input_file = os.path.join(sys.path[0], 'elements_img')  # Путь для сохранения изображений
FILENAME = ""   # Имя файла, в котором хранится изображение элемента
SCR_XY = (0, 0)  # Координаты на экране левого верхнего угла квадрата с сохраняемым элементом
thresh = []   # Список, в котором будет храниться обработанное изображение
posl_tg = 0

cursor = Database('Li_db_v1_4.db')


def _trim_to_bbox(binary_matrix: np.ndarray) -> np.ndarray:
    ys, xs = np.where(binary_matrix == 1)
    if ys.size == 0:
        return binary_matrix[:0, :0]
    return binary_matrix[min(ys):max(ys)+1, min(xs):max(xs)+1]

def stable_object_hash_from_matrix(binary_matrix: np.ndarray) -> str:
    bm = (binary_matrix > 0).astype(np.uint8)
    bm = _trim_to_bbox(bm)
    shape_bytes = np.array(bm.shape, dtype=np.uint16).tobytes()
    payload = np.packbits(bm, axis=None).tobytes()
    return hashlib.blake2b(shape_bytes + payload, digest_size=16).hexdigest()

def stable_object_hash_from_offsets(offset):
    if not offset:
        return hashlib.blake2b(b"empty", digest_size=16).hexdigest()
    width = max(offset, key=lambda x: x[1])[1] + 1
    height = max(offset, key=lambda x: x[0])[0] + 1
    matrix = np.zeros((height, width), dtype=np.uint8)
    for r, c in offset:  # offset уже нормализован к (row, col)
        matrix[r][c] = 1
    return stable_object_hash_from_matrix(matrix)

last_object_hash = None
def get_last_object_hash():
    return last_object_hash


def stiranie_pamyati():
    # Удаление лишних строчек в таблицах БД
    # print("Запущено стирание памяти")
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


def save_image(x_pos, y_pos):
    """
    Функция определяет положение курсора мыши, делает скриншот квадрата с заданными размерами и сохраняет файл с img
    """
    global SCR_XY
    # x_pos, y_pos = pyautogui.position()
    # print('Позиция мыши следующая: ', x_pos, y_pos)

    # Делаем скриншот нужного квадрата, где центр - координаты мыши
    SCR_XY = (x_pos - REGION // 2, y_pos - REGION // 2)
    image = screenshot(*SCR_XY, REGION)

    # скриншот целого экрана
    # image = screenshot()

    x = y = 0
    w = h = REGION

    # Сохраняем изображение найденного элемента
    ROI = image[y:y_pos + h, x:x_pos + w]
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    filename = f'{"_".join([BASENAME, suffix])}.png'
    cv2.imwrite(os.path.join(PATH, filename), ROI)

    return filename

def preobrazovanie_img(filename):
    """
    Функция открывает файл с сохранённым изображением, преобразовывает в ч/б и сохраняет в csv
    """

    img = np.asarray(Image.open(os.path.join(PATH, filename)))

    image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    # преобразовать изображение в формат оттенков серого
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Применение бинарного порога к изображению
    ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

    # сохранение scv файла в цвете в csv:
    # np.savetxt(f"{PATH}/{filename}.csv", img.reshape(REGION, -1), delimiter=",", fmt="%s", header=str(img.shape))

    # np.savetxt(f"{PATH}/{filename}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл
    # print('thresh:\n', thresh)

    return thresh


def save_matrix(thresh):
    """ Точки объектов - 1, фон - 0, сохраняет матрицу в файл Preobrazovanniy"""

    thresh[thresh == 255] = 1  # Меняем в массиве 255 на 1

    # Определяем, что является чернилами
    ink = 1 if sum(np.sum(i == 1) for i in thresh) < (len(thresh) * len(thresh[0])) // 2 else 0

    # Меняем чернила на 1, а фон на 0
    if not ink:
        mask = thresh ^ 1
        thresh = mask.astype(np.uint8)


    filename = "Preobrazovanniy"

    np.savetxt(f"{os.path.join(PATH, filename)}.csv", thresh, delimiter=" ,", fmt=" %.0f ")  # сохранение в csv-файл

    return thresh


def spiral(x, y, n):
    """ Это функция генератор, ее надо инициализировать и далее с помощью оператора next получать координаты
     a = spiral(3, 3, 3)
     x, y = next(a)
     x, y координаты центра, n - количество слоев """
    x = [x]
    y = [y]
    end = y[0] + n + 1
    xy = [y, x, y, x]  # у - по вертикали, x - по горизонтали
    where = [1, 1, -1, -1]  # Движение: вниз, вправо, вверх, налево
    stop = [xy[i][0]+where[i] for i in range(4)]
    i = 0
    while y[0] < end:
        while True:
            yield (x[0], y[0])
            xy[i][0] = xy[i][0] + where[i]
            if xy[i][0] == stop[i]:
                stop[i] = stop[i] + where[i]
                break
        i = (i + 1) % 4


def fill(matrix, x, y):
    """ Обход точек и формирование списка смещения каждой относительно верхнего левого угла 0, 0"""
    out = []
    stack = [(x, y)]
    while stack:
        x, y = stack.pop()
        if matrix[x][y] == 1:
            matrix[x][y] = 2
            out.append((x, y))
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == dy == 0:
                        continue
                    new_x = x + dx
                    new_y = y + dy
                    if 0 <= new_x < matrix.shape[0] and 0 <= new_y < matrix.shape[1]:
                        stack.append((new_x, new_y))
    return out


def sozdat_new_tochky(name, work, type, func, porog, signal, puls, rod1, rod2):
    max_ID = cursor.execute("SELECT MAX(ID) FROM glaz").fetchone()
    new_id = max_ID[0] + 1
    cursor.execute("INSERT INTO glaz VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id, name, work, type, func, porog, signal, puls, rod1, rod2, name))
    return new_id


def sozdat_svyaz(id_start: int = 0, id_finish: int = 0, koord_start: int = 0):
    max_ID_svyazi = tuple(cursor.execute("SELECT MAX(ID) FROM svyazi_glaz"))
    for max_ID_svyazi1 in max_ID_svyazi:
        old_id_svyazi = max_ID_svyazi1[0]
        new_id_svyazi = old_id_svyazi + 1
    cursor.execute("INSERT INTO svyazi_glaz VALUES (?, ?, ?)", (new_id_svyazi, id_start, id_finish))


def save_to_bd(spisok):
    """
    Запись уникального объекта в БД из сортированного списка offset.
    Имеются внутренние точки таблицы (glaz), описывающие смещение относительно начальной точки (0, 0): (0, 0), (0, 1),
    (2,2) и т.п.
    Имеются внутренние временные точки (tg).
    1. Перебираем список последовательности закраски изображения.
    2. Найти соответствующую этому смещению точку в БД, если нет - создать
    3. Найти смежную (tg) между posl_tg и текущей точкой смещения
        3.1. Если нет - создать
        3.2. Если есть - присвоить ей posl_tg
    4. Создать связь между текущей координатой и tg
    """

    """ Обход точек и формирование списка смещения каждой точки от заданной """
    global posl_koord
    global posl_tg

    for (y, x) in spisok:
        name_sdvig = str(y) + "_" + str(x)
        # print(name_sdvig)
#       # поиск имеется ли точка в БД, соответствующая этому смещению
        poisk_smesheniya = tuple(cursor.execute("SELECT ID FROM glaz WHERE name = ?", (name_sdvig,)))
        if not poisk_smesheniya:
            # если нет - создать
            new_sdvig = sozdat_new_tochky(name_sdvig, 0, 'sdvig', 'zazech_sosedey', 1, 0, 0, posl_tg, 0)
        else:
            for poisk_smesheniya1 in poisk_smesheniya:
                new_sdvig = poisk_smesheniya1[0]
        # найти связующее tg м/у posl_tg и точкой сдвига
        poisk_svyazyushei_tg_s_new_smeshenie = tuple(cursor.execute(
            "SELECT ID FROM glaz WHERE rod1 = ? AND rod2 = ?", (posl_tg, new_sdvig)))
        if not poisk_svyazyushei_tg_s_new_smeshenie:
            new_tg = sozdat_new_tochky('time_g', 0, 'time', 'zazech_sosedey', 1, 0, 0, posl_tg, new_sdvig)
            # sozdat_svyaz(0, new_tg, new_smeshenie)
            sozdat_svyaz(posl_tg, new_tg)
            sozdat_svyaz(new_sdvig, new_tg)
            posl_tg = new_tg
        else:
            for poisk_svyazyushei_tg_s_new_smeshenie1 in poisk_svyazyushei_tg_s_new_smeshenie:
                posl_tg = poisk_svyazyushei_tg_s_new_smeshenie1[0]

# ----------------------------------------------------------------------------


def encode_and_save_to_db_image(x_pos, y_pos):
    """ Получение координат клика мыши
     """
    print(screen.get_screen())
    print(screen.list_search(x_pos, y_pos))

    global posl_tg
    filename = save_image(x_pos, y_pos)

    # 3. Преобразовать скриншот в матрицу из 1 и 0, где 0 — это фон, 1 — точки объекта
    matrix = preobrazovanie_img(filename)
    matrix = save_matrix(matrix)

    # 4. Методом спирали найти ближайшую к клику мыши точку объекта
    sp = spiral(REGION//2, REGION//2, 3)
    try:
        while True:
            x, y = next(sp)
            if matrix[x][y] == 1:
                # print(' Координаты точки:', x, y)
                break
    except StopIteration:
        print('Не найдено точки объекта')
        exit()

    # print('\nИсходный скриншот\n', matrix)

    # 5. Получить список кортежей смещений каждой точки объекта относительно левой верхней точки квадрата скриншота.
    #    Полученный список теперь содержит только один объект, точка которого была найдена в п.4. Он мог находиться
    #    в центре сделанного скриншота.
    offset = fill(matrix, x, y)

    # 6. Найти минимальное значение смещений по горизонтали и вертикали
    min_y = min(offset, key=lambda x: x[0])[0]
    min_x = min(offset, key=lambda x: x[1])[1]

    # 7. Уменьшить все координаты горизонтали и вертикали на их минимальные значения. Таким образом сдвигаем объект в
    #    верхний левый угол.
    offset = [(y - min_y, x - min_x) for y, x in offset]

    # print('\nСписок смещений\n')
    # print(offset)
    # Отсортировать список кортежей по возрастанию по первому элементу (по вертикали), а затем по второму (по горизонтали)
    offset.sort(key=lambda x: (x[0], x[1]))
    # print('\nСписок смещений отсортированный\n')
    # print(offset)

    # 8. Ширина описывающего прямоугольника — макс. горизонтальное смещение + 1, высота макс. вертикальное смещение + 1.
    width = max(offset, key=lambda x: x[1])[1] + 1
    height = max(offset, key=lambda x: x[0])[0] + 1
    # print()
    # print(f'Ширина: {width}')
    # print(f'Высота: {height}')

    # Восстановить рисунок из списка смещений в матрице минимальных размеров
    matrix = np.zeros((height, width), dtype=int)
    for dx, dy in offset:
        matrix[dx][dy] = 1
    # print('\nВыбранный объект в матрице минимальных размеров\n', matrix)

    # 9. Координаты верхнего левого угла прямоугольника (объекта) на экране — координаты скриншота +
    #    значения найденные в п.6.
    # print('\nКоординаты верхнего левого угла прямоугольника (объекта) на экране')
    # print(SCR_XY[0] + min_x, SCR_XY[1] + min_y)


    # stiranie_pamyati()
    global last_object_hash
    last_object_hash = stable_object_hash_from_offsets(offset)
    print(f"OBJECT_HASH={last_object_hash}")
    save_to_bd(offset)

    # print(f"posl_tg для записи к posl_t0 такой: {posl_tg}")
    posl_tg1 = posl_tg
    posl_tg = 0

    cursor.commit()
    return posl_tg1

if __name__ == '__main__':
    print('Наведите курсор на объект,\nНажмите Ctrl, чтобы сделать скриншот\n')

    # Далее работа по алгоритму new_examole. Найти один объект, преобразовать в новую матрицу
    def on_press(key):
        global SCR_XY
        x_pos, y_pos = pyautogui.position()
        SCR_XY = x_pos, y_pos
        listener.stop()


    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
# ----------------------------------------------------------------------------

    encode_and_save_to_db_image(*SCR_XY)