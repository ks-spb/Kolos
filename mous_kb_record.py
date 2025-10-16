from time import sleep
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as kb_Controller, Listener as KeyboardListener
from pynput.mouse import Button, Controller
import pyautogui
import json
import cv2
import numpy as np

import report
from exceptions import *
from report import report
from screen import screen
from db import Database

listener_kb = KeyboardListener()  # Слушатель клавиатуры
kb = kb_Controller()
mo = Controller()

""" Вид в котором информация о событиях хранится объекте:
    
    Нажата клавиша 'A': {'type': 'kb', 'event': 'down', 'key': 'A'}
    Отпущена клавиша 'A': {'type': 'kb', 'event': 'up', 'key': 'A'}

    Нажата левая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.left', 'x': 671, 'y': 591, 
    'image': id}
    Нажата правая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.right', 'x': 671, 'y': 591, 
    'image': id}
    Нажата левая клавиша мыши: {'type': 'mouse', 'event': 'click', 'image': hash}
    --- Поскольку в новой версии изображение сохраняется в БД, то пишем только id вместо имени файла ---
    
    Отпущена левая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.left', 'x': 671, 'y': 591}
    Отпущена правая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.right', 'x': 671, 'y': 591}
"""


class Hotkey:
    """ Замена горячих клавиш на id или заданное имя. Дополнительные методы обработки.

    Список сочетаний и последовательностей клавиш хранится в таблице hotkey БД в поле list в формате JSON.
    Он читается при инициализации программы и обновляется при изменениях.
    Сочетания характеризуются тем, что вначале идет нажатие одной из модификационных клавиши: Ctrl, Alt, Cmd.
    В нем записаны это и все последующие нажатия и отпускания клавиш до отпускания последней модификационной клавиши.
    При этом нажатие любой клавиши записывается как просто ее название (например 'A')
    а отпускание клавиши как 'A up'.
    """

    def __init__(self):
        # TODO: Нет защиты от повторного нажатия модификационной клавиши Левой + Правой
        # TODO: При длительном удержании записывается повтор
        self.ctrl = False  # Помнит, нажата ли клавиша Ctrl
        self.alt = False  # Помнит, нажата ли клавиша Alt
        self.cmd = False  # Помнит, нажата ли клавиша Cmd
        self.record_order = []  # Хранит сочетание текущей записи
        self.cursor = Database('Li_db_v1_4.db')  # Подключение к БД

        # Читаем из ДБ существующие последовательности, подставляя имена вместо id если они есть
        # TODO: Допускаются одинаковые имена сочетаний, добавляемые позже будут заменять прежние
        orders = self.cursor.execute("SELECT * FROM hotkey").fetchall()
        self.all_orders = {}  # Словарь списков сочетаний (ключ - номер или имя, если оно есть)
        for event in orders:
            name = str(event[0]) if not event[2] else event[2]
            self.all_orders[name] = json.loads(event[1])

    def add_to_order(self):
        """ Добавление сочетания в словарь сочетаний и в ДБ

        Возвращает id или имя последовательности.
        """
        for name, order in self.all_orders.items():
            if self.record_order == order:
                self.record_order.clear()
                return name  # Если такая последовательность уже есть, вернем ее название

        # Добавление новой последовательности
        self.cursor.execute("INSERT INTO hotkey (list) VALUES (?)", (json.dumps(self.record_order),))
        self.cursor.commit()
        id = str(self.cursor.get_last_id())
        self.all_orders[id] = self.record_order.copy()
        self.record_order.clear()
        return id

    def add_event(self, event):
        """ Добавление событие event в последовательность, если оно относится к сочетанию.

         Проверяем, начато ли сочетание (нажаты Ctrl, Alt, Cmd). Если начато, то новое
         нажатие или отпускание клавиши добавляем к сочетанию и закрываем его, если оно завершено.
         Завершено - значит отпущена последняя модификационная клавиша.

         При закрытии сочетание добавляется в список и возвращается событие в виде:
         {'type': 'kb', 'event': 'hotkey', 'key': 'id или имя сочетания'}
         Если не закрыто - вернет None.
         """
        mod = False  # Модификационная клавиша не нажата и не отпущена
        if 'ctrl' in event['key'] or 'alt' in event['key'] or 'cmd' in event['key']:
            mod = True

        if not self.ctrl | self.alt | self.cmd | mod:
            # Выходим, если событие не связано с сочетанием
            return event

        key = event['key'] + ' up' if event['event'] == 'up' else event['key']  # Какая клавиша нажата или отпущена

        # Меняем состояние модификационных клавиш
        mod = False if event['event'] == 'up' else True  # Модификационная клавиша нажата или отпущена
        if 'ctrl' in key:
            self.ctrl = mod
        elif 'alt' in key:
            self.alt = mod
        else:
            self.cmd = mod

        self.record_order.append(key)  # Добавляем событие в текущую последовательность

        if not self.ctrl | self.alt | self.cmd:
            # Если отпущена последняя модификационная клавиша, то закрываем последовательность
            # И возвращаем ее для записи
            event['event'] = 'hotkey'  # Помечаем, что это сочетание клавиш
            event['key'] = self.add_to_order()  # Добавляем сочетание в словарь и возвращаем его id или имя
            return event

        return None

    def get_order(self, name):
        """ Получение последовательности по имени

        Принимает имя последовательности.
        Возвращает последовательность событий готовых для воспроизведения."""
        print(f'Работа функции get_order в mouse_kb_record. name = {name}')
        order = []
        for event in self.all_orders[name]:
            if 'up' in event:
                order.append({'type': 'kb', 'event': 'up', 'key': event[:-3]})
            else:
                order.append({'type': 'kb', 'event': 'down', 'key': event})

        return order

    def tap_key(self, event):
        """ Превращает события нажатия и отпускания клавиши в одно - tap

        Метод должен обрабатывать события последним. Он пропустит событие нажатия клавиши, вернув пустое событие
        и добавит при событии отпускания - общее событие нажатия и отпускания клавиши как tap.

        Исключение: Shift

        Нажата клавиша 'A': {'type': 'kb', 'event': 'down', 'key': 'A'}
        Отпущена клавиша 'A': {'type': 'kb', 'event': 'up', 'key': 'A'}

        При нажатии вернет None,
        при отпускании {'type': 'kb', 'event': 'tap', 'key': 'A'}"""
        if 'shift' in event['key']:
            return event

        if event['event'] == 'down':
            return None
        elif event['event'] == 'up':
            return {'type': 'kb', 'event': 'tap', 'key': event['key']}
        return event


hotkey = Hotkey()  # Создание объекта обработки сочетаний клавиш


def screenshot(x_reg: int = 0, y_reg: int = 0, region: int = 0):
    """ Скриншот заданного квадрата или всего экрана

    В качестве аргументов принимает координаты верхней левой точки квадрата и его стороны.
    Если сторона на задана (равна 0) - то делает скриншот всего экрана

    """
    if region:
        # print(f'screenshot. Если есть регион: {region}')
        image = pyautogui.screenshot(
            region=(x_reg, y_reg, region, region))  # x, y, x+n, y+n (с верхнего левого угла)
        # print(f'screenshot. Получается скриншот: {image}')
    else:
        image = pyautogui.screenshot()
        # print(f'screenshot. Region отсутствует - поэтому скриншот: {image}')
        # print(
        #     f'screenshot. cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR): {cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)}')
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


class Recorder:
    """ Прослушивание мыши и клавиатуры и запись событий с них """

    status = False  # Чтение с мыши и клавиатуры запрещено
    record = []  # В списке в порядке поступления хранятся события мыши и клавиатуры в виде кортежа словарей
    key_down = ''  # Помнит, какая клавиша нажата, для использования во внешних модулях
    queue_hashes = None  # Получаем сюда ссылку на очередь с элементами экрана

    def start(self):
        """ Начать запись """
        self.record.clear()  # Удаление старой записи перед началом новой
        self.status = True

        # ----------------------------------
        # Создание отчета в виде изображений
        report.set_folder('record')  # Инициализация папки для сохранения изображений
        # ----------------------------------

    def stop(self):
        """ Остановить запись """
        self.status = False

    def on_press(self, key):
        """ Запись нажатой клавиши """
        if key == keyboard.Key.esc:
            # Остановка записи по клавише Esc
            self.stop()
            self.key_down = ''
            return

        try:
            out = listener_kb.canonical(key).char
            if not out:
                raise
        except:
            out = str(key)
            if key == keyboard.Key.space:
                # Обработка пробела отдельно
                out = ' '

        # Нажата клавиша, она должна быть добавлена в запись,
        # но может быть она относится последовательности
        event = hotkey.add_event({'type': 'kb', 'event': 'down', 'key': out})  # Какое событие нужно добавить
        event = hotkey.tap_key(event)  # Превращаем события нажатия и отпускания клавиши в одно - tap
        if event:
            # Добавляем нажатие кнопки или выполнение последовательности
            self.record.append(event)

    def on_release(self, key):
        """ Запись отпущенной клавиши """
        try:
            out = listener_kb.canonical(key).char
            if not out:
                raise
        except:
            out = str(key)
            if key == keyboard.Key.space:
                # Обработка пробела отдельно
                out = ' '

        # Отпущена клавиша, она должна быть добавлена в запись,
        # но может быть она относится последовательности
        event = hotkey.add_event({'type': 'kb', 'event': 'up', 'key': out})  # Какое событие нужно добавить
        event = hotkey.tap_key(event)  # Превращаем события нажатия и отпускания клавиши в одно - tap
        if event:
            # Добавляем отпускание кнопки или выполнение последовательности
            self.record.append(event)



    def on_click(self, x, y, button, is_pressed):
        """ Запись нажатия и отпускания кнопки мыши происходит,
        если определен объект на котором был клик """
        if not is_pressed:
            return  # Если кнопка отпущена, то ничего не записываем

        # hash_element = screen.list_search(x, y)  # Поиск элемента на экране по координатам клика
        hash_element = screen.element_under_cursor()   # 21.03.24 - Поиск элемента под курсором
        print(f'Объект под курсором для записи действий: {hash_element}')

        # -------------------------------
        # Сохранение изображений в отчете
        scr = report.circle_an_object(screenshot(), screen.hashes_elements.values())  # Обводим элементы
        report.save(scr, screen.get_element(hash_element))  # Сохранение скриншота и элемента
        # -------------------------------

        if not hash_element:
            # Если элемент не найден, то выходим
            print("**** ВНИМАНИЕ! Хэш элемента не найден на экране! Запись последовательности прервана! ****************")
            out = {'type': 'mouse', 'event': 'click', 'image': hash_element, 'x': x, 'y': y}
            self.record.append(out)
            return

        # Записываем перемещение мыши
        out = {'type': 'mouse', 'event': 'click', 'image': hash_element, 'x': x, 'y': y}
        self.record.append(out)


rec = Recorder()  # Создаем объект записи


def on_press(key):
    """ Действие, когда пользователь нажимает клавишу на клавиатуре """

    # Записываем нажатую клавишу, для использования во внешних модулях
    try:
        rec.key_down = key.char
    except:
        rec.key_down = str(key)

    if rec.status:
        rec.on_press(key)


def on_release(key):
    """ Действие, когда пользователь отпускает клавишу на клавиатуре """

    if rec.status:
        rec.on_release(key)


def on_click(x, y, button, is_pressed):
    """ Действие при нажатии кнопки мыши """
    if rec.status:
        rec.on_click(x, y, button, is_pressed)


keyboard_listener = keyboard.Listener(on_press=on_press,
                                      on_release=on_release)  # Инициализация прослушивания клавиатуры
mouse_listener = mouse.Listener(on_click=on_click)  # Инициализация прослушивания мыши

mouse_listener.start()  # Старт прослушивания мыши
keyboard_listener.start()  # Старт прослушивания клавиатуры


# rec.start()
# while True:
#     sleep(0.001)


class Play:
    """ Класс для воспроизведения записанных событий клавиатуры и мыши """

    gap = 0.3  # Промежуток между нажатиями клавиш и кликами мыши при воспроизведении (МС)
    duration = 0.001  # Длительность удержания кнопки нажатой (мыши и клавиатуры)

    # В текущей реализации отсутствуют понятия перетаскивания, выделения, поэтому координаты отпускания клавиш мыши
    # считаются теми же, в которых они были нажаты
    button_up = {}  # Координаты отпускания правой/левой клавиши мыши. Пример: {'button.left': (x, y)}

    def play_one(self, action):
        """ Воспроизведение одного действия """

        print(f'Работа функции play_one в файле mouse_kb_record self = {self}, action = {action}')

        if action['type'] == 'kb' and action['event'] == 'hotkey':
            # Воспроизведение последовательности клавиш
            # print('Это ведь игнорируется?')
            self.play_list(hotkey.get_order(action['key']))
            return

        # print(f"Дошли сюда? action[event] = {action['event']}")

        if action['event'] == 'click':
            # Перемещение мыши к заданной позиции
            # Позиция определяется по центру элемента хэш которого указан в action['image']
            # print(f'Выполнение клика мыши. action[image]: = ')

            # 02.07.25 - заккоментировал т.к. не происходил клик
            # if action['image']:
            #     res = screen.get_hash_element(action['image'])
            #     print(f'res = {res}')
            #     # -------------------------------
            #     # Сохранение изображений в отчете
            #     scr = report.circle_an_object(screen.screenshot, screen.hashes_elements.values())  # Обводим элементы
            #     report.save(scr, screen.get_element(action['image']))  # Сохранение скриншота и элемента
            #     # -------------------------------
            # print(f'res 2 = {res}')

            # if res:
            #     # pyautogui.moveTo(*res, 0.3)
            #     pyautogui.click(*res, button='left')
            # else:
            print('Нужно просто кликнуть мышкой и всё...')
            pyautogui.click(button='left')

            return

        if action['event'] == 'move':
            # Просто перемещение мыши к позиции
            koord_x = action['x']
            koord_y = action['y']
            pyautogui.moveTo(int(koord_x), int(koord_y), 0.3)

        if action['type'] == 'kb':
            # Работа с клавиатурой
            # Подготовка к распознаванию как отдельных символов, так и специальных клавиш
            insert = action['key']
            if len(action['key']) == 1:
                insert = f"'{insert}'"

            print(f'Работаем с клавиатурой в play_one')

            if action['event'] == 'down':
                # Нажатие клавиши
                exec(f"kb.press({insert})")
            elif action['event'] == 'up':
                # Отпускание клавиши
                sleep(self.duration)  # Удержание клавиши нажатой
                exec(f"kb.release({insert})")
                sleep(self.gap)  # Пауза между нажатиями и/или кликами
            else:
                # Нажатие и отпускание клавиши
                insert = "Key.enter"
                print(f"Должно произойти нажатие и отпускание клавиши. insert = {insert}")
                exec(f"kb.tap({insert})")

                sleep(self.gap)  # Пауза между нажатиями и/или кликами

        else:
            print('play_one. Дошли до else...')
            # Ставим указатель мыши в нужную позицию

            # mo.position = (action['x'], action['y'])

            # Нажатие и отпускание кнопки мыши
            if action['event'] == 'down':
                print('play_one. action[event] == down')

                if action['image']:
                    print(f'Дошли до сюда? if action[image] = {action['image']}')
                    res = screen.get_hash_element(action['image'])
                    print(f'Найдена следующая res = {res}')
                    if res:
                        print(f'Найдены координаты изображения res = {res}')
                        # -------------------------------
                        # Сохранение изображений в отчете
                        scr = report.circle_an_object(screen.screenshot, screen.hashes_elements.values())  # Обводим элементы
                        report.save(scr, screen.get_element(action['image']))  # Сохранение скриншота и элемента
                        # -------------------------------
                    else:
                        print('Элемент не найден на экране')
                print(f'res 2 = {res}')

                if res:
                    # pyautogui.moveTo(*res, 0.3)
                    pyautogui.click(*res, button='left')

                # 04.07.25 - Ниже старый вариант кода
                # Проверяем, есть ли нужный элемент под курсором и если нет,
                # пытаемся найти его на экране, ожидаем и повторяем попытку на случай долгого открытия приложения
                # rep = 3
                # while rep:
                #
                #     try:
                        # x = action['x']
                        # y = action['y']
                        # x, y = pattern_search(action['image'], x, y)  # Поиск элемента на экране
                        # mo.position = (x, y)
                        # self.button_up[action['key']] = (x, y)  # Координаты отпускания для левой или правой клавиш мыши
                        # exec(f"mo.press({insert})")
                        # rep = 0

                    # Ошибки при поиске элемента
                    # except TemplateNotFoundError as err:
                    #     print(err)
                    #     raise
                    #
                    # except ElementNotFound as err:
                    #     print(err, 'Ожидание приложения...')
                    #     sleep(1)
                    #     rep -= 1
                    #     if not rep:
                    #         print(err)
                    #         raise
            else:
                # Отпускание клавиши
                if action['event'] != 'move':
                    sleep(self.duration)  # Удержание клавиши нажатой

                    if self.button_up[action['key']]:
                        # Координаты в которых должна быть отпущена клавиша мыши, запомнены, при ее нажатии
                        mo.position = self.button_up[action['key']]

                    # exec(f"mo.release({insert})")

                    sleep(self.gap)  # Пауза между нажатиями и/или кликами

    def play_list(self, order):
        """ Воспроизведение событий из списка """
        print('Воспроизведение последовательности', order)
        for event in order:
            self.play_one(event)


play = Play()  # Экземпляр проигрывателя
