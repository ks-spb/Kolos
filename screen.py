"""Служит для получения и обновления в основном процессе информации об экране
Модуль, содержащий класс, для считывания информации о текущем экране из очереди,
куда она поставляется параллельным процессом детектирующим изменения экрана
и производя первичную обработку и подготовку данных (screen_monitoring.py).
Формат данных описан в модуле screen_monitoring.
"""

import time
import numpy as np
import cv2


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
            dist = cv2.pointPolygonTest(rect_contour, (x_point, y_point), False)
            print(dist)
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
            print('Элемент не найден при воспроизведении')
            return None

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


screen = Screen()  # Создаем объект для хранения информации об элементах текущего экрана
