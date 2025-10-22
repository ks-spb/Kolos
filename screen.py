"""Служит для получения и обновления в основном процессе информации об экране
Модуль, содержащий класс, для считывания информации о текущем экране из очереди,
куда она поставляется параллельным процессом детектирующим изменения экрана
и производя первичную обработку и подготовку данных (screen_monitoring.py).
Формат данных описан в модуле screen_monitoring.

Добавлен метод нахождения элемента под курсором и получение его хэша.
"""
import time
import numpy as np
import cv2
import pyautogui

VERBOSE = False
# Список для хранения всех хэшей на текущем экране
tekyshie_img_hash = []

def _log_get_screen(msg: str, every_sec: float = 1.0):
    """Печатает msg не чаще 1 раза в `every_sec` секунд и только при VERBOSE=True."""
    global _LAST_GET_SCREEN_LOG
    if not VERBOSE:
        return
    now = time.time()
    if now - _LAST_GET_SCREEN_LOG >= every_sec:
        print(msg)
        _LAST_GET_SCREEN_LOG = now

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

    global tekyshie_img_hash

    def get_screen(self):
        """Получает из очереди информацию о текущем экране (обновление данных)
        Вернет True если обновил.
        Изменит дату последнего обновления.
        """
        global tekyshie_img_hash
        # print('Работа функции get_screen')
        if self.queue_hashes is None:
            print("get_screen. if self.queue_hashes is None")
            return False

        if not self.queue_hashes.empty():
            print('get_screen. if not self.queue_hashes.empty()')
            # Получаем данные из очереди
            tmp = self.queue_hashes.get()

            # Вывод всех хэшей экрана в список
            filtered_hash = [key for key in tmp[1].keys()]
            # print(f'screen. Отфильтрованные ключи из tmp: {filtered_hash}')  # screen. Отфильтрованные ключи из tmp: ['1400150000000000', '5404415015000004', '509d5b62e9f4870a', '80a07103b1994e4a', '48a83113ef2f5e5e',
            tekyshie_img_hash = filtered_hash

            self.screenshot, self.screenshot_hash = tmp[0]
            self.hashes_elements = tmp[1]
            # print(f'self.hashes_elements = tmp[1] = {tmp[1]}')   # self.hashes_elements = tmp[1] = {'1400150000000000': [118, 1072, 6, 3], '5404415015000004': [1625, 1053, 12, 6], '509d5b62e9f4870a': [1721, 1052, 24, 10], '80a07103b1994e4a': [769, 1052, 56, 13],
            self._last_update = time.time()
            return True
        else:
            # print('get_screen выдал else')
            return False

    def tekysie_hash(self):
        global tekyshie_img_hash
        return tekyshie_img_hash

    def list_search(self, x_point, y_point, inside_pad: int = 0):
        """Ищет элемент, в чьём прямоугольнике лежит точка (x_point, y_point).
           Возвращает ХЭШ элемента или None.
           inside_pad — расширение прямоугольника на указанное число пикселей по всем сторонам.
        """
        self.get_screen()

        if not self.hashes_elements:
            return None  # Нет элементов

        candidate, min_square = None, None  # если точка попала сразу в несколько, берём с минимальной площадью
        for h, (x, y, w, hgt) in self.hashes_elements.items():
            # расширим bbox на inside_pad
            x0 = x - inside_pad
            y0 = y - inside_pad
            x1 = x + w + inside_pad
            y1 = y + hgt + inside_pad

            # точка внутри?
            if x0 <= x_point <= x1 and y0 <= y_point <= y1:
                sq = w * hgt
                if min_square is None or sq < min_square:
                    min_square = sq
                    candidate = h

        # Строгое поведение: если ни один прямоугольник не содержит точку — возвращаем None
        return candidate


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

    def get_all_hashes(self):
        """Возвращает список всех хэшей элементов экрана"""
        print(f'screen. Все хэши на экране  self.hashes_elements: {self.hashes_elements}')
        return list(self.hashes_elements.keys())


    def get_hash_element(self, hash):
        """Возвращает координаты центра элемента по его хэшу
        или None, если элемента нет """
        print('Работа функции get_hash_element')
        # self.get_screen()
        print(f'Поиск всех хэшей на экране: {self.get_all_hashes()}')
        element = self.hashes_elements.get(hash)
        print(f'screen.get_hash_element. element = {element}')
        if not element:
            print('!!!!!Элемент не найден на экране')   # 21.03.24 - Из-за уточнения
            # объектов, приходится перемещать курсор мыши на запомненные координаты. В этом случае изображение может
            # отличаться от изображения без наведения курсора - тогда нужно взять координаты курсора мыши
            # x_kursor, y_kursor = pyautogui.position()   # 04.07.25 - Закомментировал
            return None   # 21.03.24 - Было None 04.07.25 - было x_kursor, y_kursor

        x = (element[2]) // 2
        y = (element[3]) // 2
        return element[0] + x, element[1] + y



    @property
    def last_update(self):
        """Возвращает время последнего обновления"""
        self.get_screen()
        return self._last_update

    def element_under_cursor(self):
        """Возвращает хэш элемента под курсором или None."""
        pos = pyautogui.position()
        # маленький зазор в 1–2 пикселя помогает при дрожи рамки
        return self.list_search(pos.x, pos.y, inside_pad=1)




screen = Screen()  # Создаем объект для хранения информации об элементах текущего экрана
