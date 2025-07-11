"""Служит для получения и обновления в основном процессе информации об экране
Модуль, содержащий класс, для считывания информации о текущем экране из очереди,
куда она поставляется параллельным процессом детектирующим изменения экрана
и производя первичную обработку и подготовку данных (screen_monitoring.py).
Формат данных описан в модуле screen_monitoring.

Добавлен метод нахождения элемента под курсором и получение его хэша.
"""

import numpy as np
import cv2
import pyautogui

import time


def screenshot(x_reg: int = 0, y_reg: int = 0, region: int = 0):
    """ Скриншот заданного квадрата или всего экрана

    В качестве аргументов принимает координаты верхней левой точки квадрата и его стороны.
    Если сторона на задана (равна 0) - то делает скриншот всего экрана

    """
    if region:
        # print(f'screenshot. Если есть регион: {region}')
        image = pyautogui.screenshot(region=(x_reg, y_reg, region, region))  # x, y, x+n, y+n (с верхнего левого угла)
        # print(f'screenshot. Получается скриншот: {image}')
    else:
        image = pyautogui.screenshot()
        # print(f'screenshot. Region отсутствует - поэтому скриншот: {image}')
        # print(f'screenshot. cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR): {cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)}')
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


class Screen:
    """Класс для хранения информации об элементах текущего экрана"""

    def __init__(self, queue_hashes=None):
        """Инициализация"""
        self.queue_hashes = queue_hashes  # Ссылка на очередь с информацией об элементах экрана
        self._last_update = time.time()  # Время последнего обновления
        self.screenshot = None  # Изображение экрана в формате NumPy
        self.screenshot_hash = None  # pHash изображения экрана
        self.hashes_elements = {}  # Словарь, где ключ pHash элемента экрана (кнопки, значка...),
        # а значение - список [x, y, w, h]: x, y - верхний левый угол изображения; w, h - ширина, высота.

    def get_screen(self):
        """Получает из очереди информацию о текущем экране (обновление данных)
        Вернет True если обновил.
        Изменит дату последнего обновления.
        """
        if self.queue_hashes is None:
            return False

        if not self.queue_hashes.empty():
            # Получаем данные из очереди
            tmp = self.queue_hashes.get()
            self.screenshot, self.screenshot_hash = tmp[0]
            self.hashes_elements = tmp[1]
            self._last_update = time.time()
            return True
        else:
            return False

    def list_search(self, x_point, y_point):
        """Ищет в списке элемент по координатам.
         Принимает координаты, возвращает хэш или None, если элемента нет
         Координаты должны принадлежать прямоугольнику (ищем все выбираем минимальный)
         Если такого нет, возвращаем ближайший элемент."""

        self.get_screen()
        # element = [hash for hash, coord in self.hashes_elements.items()
        #            if coord[0] < x < coord[2] and coord[1] < y < coord[3]]
        if not self.hashes_elements:
            return None  # Нет элементов

        # Находим, какому элементу принадлежат координаты места клика
        candidate, square = None, None  # Кандидат на выдачу и его площадь (контур, которому принадлежит точка)
        element, distance = None, None  # Ближайший элемент и расстояние до него
        for hash, (x, y, w, h) in self.hashes_elements.items():
            rect = np.array([[x, y], [x+w, y], [x+w, y+h], [x, y+h]])   # создаем массив вершин
            rect_contour = rect.reshape((-1,1,2))  # преобразуем в формат контура
            dist = cv2.pointPolygonTest(rect_contour, (x_point, y_point), True)
            if dist >= 0:
                # Точка внутри контура. Выбираем тот контур, у которого площадь меньше
                this_square = w * h
                if square is None or this_square < square:
                    square = this_square
                    candidate = hash
            else:
                # Точка снаружи контура. Выбираем ближайший
                dist = abs(dist)
                if distance is None or dist < distance:
                    distance = dist
                    element = hash

        # Если найден контур, которому принадлежит точка, возвращаем его
        # Иначе возвращаем ближайший
        return candidate if candidate else element

    def get_element(self, hash):
        """Возвращает изображение в формате NumPy элемента по его хэшу.
        Изображение берется из скриншота по координатам элемента или None, если хэш None"""
        if hash is None:
            return None

        self.get_screen()

        element = self.hashes_elements.get(hash)
        if not element:
            return None
        return self.screenshot[element[1]:element[1]+element[3], element[0]:element[0]+element[2]]  # y, w, x, h

    def get_hash_element(self, hash):
        """Возвращает координаты центра элемента по его хэшу
        или None, если элемента нет """
        self.get_screen()

        element = self.hashes_elements.get(hash)
        if not element:
            print('Элемент не найден при воспроизведении - взято положение курсора мыши')   # 21.03.24 - Из-за уточнения
            # объектов, приходится перемещать курсор мыши на запомненные координаты. В этом случае изображение может
            # отличаться от изображения без наведения курсора - тогда нужно взять координаты курсора мыши
            x_kursor, y_kursor = pyautogui.position()
            return x_kursor, y_kursor   # 21.03.24 - Было None

        x = (element[2]) // 2
        y = (element[3]) // 2
        return element[0] + x, element[1] + y

    def get_all_hashes(self):
        """Возвращает список всех хэшей элементов экрана"""
        return list(self.hashes_elements.keys())

    @property
    def last_update(self):
        """Возвращает время последнего обновления"""
        self.get_screen()
        return self._last_update

    def element_under_cursor(self):
        """Нахождение элемента под курсором и получение его хэша.
        Вернет Хэш элемента или None"""
        WIDTH = 100  # Ширина области, в которой ищем элемент
        HEIGHT = 100  # Высота области, в которой ищем элемент

        # Получаем координаты мыши
        x, y = pyautogui.position()

        try:
            # Находим прямоугольник
            x1, y1 = max(x - WIDTH // 2, 0), max(y - HEIGHT // 2, 0)  # Координаты не должны быть меньше 0
            x2, y2 = x1 + WIDTH, y1 + HEIGHT

            # Запоминаем координаты мыши на вырезанном участке
            cur_x, cur_y = x - x1, y - y1


            scr = screenshot()  # Получаем снимок экрана
            # print(f'element_under_cursor. Получаем снимок экрана: {scr}')   #Снимок получается
            # Вырезаем прямоугольник, в котором будем искать элемент
            region = scr[y1:y2, x1:x2]
            # print(f'element_under_cursor. region:  {region} из y1: {y1} и x1: {x1}')

            # Применяем Canny алгоритм для поиска границ
            edges = cv2.Canny(region, 100, 200)

            # Применяем морфологическую операцию закрытия
            kernel = np.ones((3, 3), np.uint8)
            # closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            closed = cv2.dilate(edges, kernel, iterations=2)

            # Ищем контуры и проходим по ним
            contours, hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # -----------------------------------------------------------------------
            # Это добавлено при отладке и может быть удалено, для работы не нужно
            # print(len(contours))
            # cv2.imwrite("1\image_screenshot.jpg", screen.screenshot)
            # s = 0
            # -----------------------------------------------------------------------

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)

                # Ищем элемент, которому принадлежат координаты мыши
                rect = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]])  # Создаем массив вершин
                rect_contour = rect.reshape((-1, 1, 2))  # преобразуем в формат контура
                dist = cv2.pointPolygonTest(rect_contour, (cur_x, cur_y), True)

                # -----------------------------------------------------------------------
                # Это добавлено при отладке и может быть удалено, для работы не нужно
                # print(f'X {x} - {x+w}, а курсор {cur_x}\nY {y} - {y+h}, а курсор {cur_y}')
                # w1, h1 = x + w, y + h
                # segment = region[y:h1, x:w1]
                #
                # hash = cv2.img_hash.pHash(segment)  # Получаем хэш сегмента
                # hash = np.array(hash).tobytes().hex()  # Преобразование хэша в шестнадцатеричную строку
                #
                # # Сохранить изображение с именем, содержащим текущее время
                # cv2.imwrite("1\image_" + hash + ".jpg", segment)
                #
                # s += 1
                # ---------------------------------------------------------------------
                if dist >= 0:
                    w1, h1 = x + w, y + h
                    segment = region[y:h1, x:w1]
                    # cv2.imshow("Rectangle Image", segment)
                    # cv2.waitKey(0)
                    hash = cv2.img_hash.pHash(segment)  # Получаем хэш сегмента
                    return np.array(hash).tobytes().hex()  # Преобразование хэша в шестнадцатеричную строку
        except:
            pass
        return None


screen = Screen()  # Создаем объект для хранения информации об элементах текущего экрана
