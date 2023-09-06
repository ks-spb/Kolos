# Программа собирает элементы экрана в фоновом режиме
# Для этого создается новый процесс (программа работает на отдельном ядре процессора)
# При работе программа регистрирует изменения экрана и на каждом новом экране
# производит поиск элементов, после чего записывает их в очередь, удаляя предыдущий экран из нее

# Какая информация записывается в очередь на выход:
# ((screenshot, screenshot_hash), hashes_elements)
# screenshot - изображение экрана в формате NumPy
# screenshot_hash - pHash изображения screenshot
# hashes_elements - словарь, где ключ pHash элемента экрана (кнопки, значка...),
# а значение - список [x, y, w, h]: x, y - верхняя левая точка,  w, h - нижняя правая точка.

import mss
import mss.tools
import cv2
from threading import Thread
import time
import numpy as np


def screen_monitor(queue_img):
    """ Запускает поток, который делает скриншоты с заданной периодичностью
    и сообщает если экран изменился. """
    sct = mss.mss()
    monitor = {'top': 0, 'left': 0, 'width': sct.monitors[0]['width'], 'height': sct.monitors[0]['height']}
    hash_base_img = None  # Получаем хэш сегмента

    while True:
        scr_img = sct.grab(monitor)  # Делаем скриншот
        img = np.asarray(scr_img)  # Записываем его в np
        hash_img = cv2.img_hash.pHash(img)  # Получаем хэш сегмента

        if hash_base_img is None or (cv2.norm(hash_base_img[0], hash_img[0], cv2.NORM_HAMMING) > 12):
            # Изображения разные
            hash_base_img = hash_img  # Сохраняем новый хэш
            queue_img.put((img, hash_img))  # Передаем скриншот и хэш в очередь

        time.sleep(0.3)  # Пауза


def process_changes(queue_hashes, queue_img):
    """ При каждом обновлении экрана очищает выходной список и начинает заполнять его снова
        разбирая полученный скриншот. По окончании данные помещает в очередь. """
    print('Запуск процесса')
    # Запускаем поток для мониторинга
    thread = Thread(target=screen_monitor, args=(queue_img,))
    thread.start()
    hashes_elements = {}

    while True:

        if not queue_img.empty():
            # Измеряем время выполнения
            start_time = time.time()

            # Получен новый скриншот, выберем из него элементы
            screenshot, screenshot_hash = queue_img.get()  # Получаем скриншот и его хэш из очереди
            print('Экран изменился ---------------------------------- ')
            # Принимает изображение типа Image
            # возвращает итератор координат и размеров всех элементов на изображении
            # в виде: [[x, y, w, h], ...] (x, y - верхняя левая точка,  w, h - нижняя правая точка)

            # Применяем Canny алгоритм для поиска границ
            edges = cv2.Canny(screenshot, 100, 200)

            # Применяем морфологическую операцию закрытия
            kernel = np.ones((7, 7), np.uint8)
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

            # Ищем контуры и проходим по ним
            contours, hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            hashes_elements.clear()

            for cnt in contours:
                # Находим прямоугольник
                x, y, w, h = cv2.boundingRect(cnt)
                w, h = x + w, y + h
                segment = screenshot[y:h, x:w]

                hash = cv2.img_hash.pHash(segment)  # Получаем хэш сегмента
                hash_string = np.array(hash).tobytes().hex()  # Преобразование хэша в шестнадцатеричную строку

                if hash_string not in hashes_elements.keys():
                    # Если хэша нет в списке, то добавляем его
                    hashes_elements[hash_string] = [x, y, w, h]

                if not queue_img.empty():
                    # Если за время обработки скриншота экран снова изменится
                    # начинаем заново
                    break
            else:
                # Если скриншот обработан, то передаем его, его хэш и список хэшей элементов в очередь
                # Предварительно очистив ее
                while not queue_hashes.empty():
                    queue_hashes.get()
                queue_hashes.put(((screenshot, screenshot_hash), hashes_elements))
                print(f'Количество элементов последнего экрана: {len(hashes_elements)}')
                # Выводим время выполнения
                print(f'Время выполнения: {time.time() - start_time + 0.05} сек.')

