from time import sleep
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as kb_Controller
from pynput.mouse import Button, Controller
import pyautogui

import report
# from element_images import save_image, pattern_search
from image_definition import encode_and_save_to_db_image
from exceptions import *
from report import ImageReport
from screen import screen


kb = kb_Controller()
mo = Controller()


""" Вид в котором информация о событиях хранится объекте:
    
    Нажата клавиша 'A': {'type': 'kb', 'event': 'down', 'key': 'A'}
    Отпущена клавиша 'A': {'type': 'kb', 'event': 'up', 'key': 'A'}

    xxxНажата левая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.left', 'x': 671, 'y': 591, 
    'image': id}
    Нажата правая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.right', 'x': 671, 'y': 591, 
    'image': id}
    Нажата левая клавиша мыши: {'type': 'mouse', 'event': 'click', 'image': hash}
    --- Поскольку в новой версии изображение сохраняется в БД, то пишем только id вместо имени файла ---
    
    Отпущена левая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.left', 'x': 671, 'y': 591}
    Отпущена правая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.right', 'x': 671, 'y': 591}
"""

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
        self.report = ImageReport()
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
            out = key.char
        except:
            out = str(key)
            if key == keyboard.Key.space:
                # Обработка пробела отдельно
                out = ' '

        self.record.append({'type': 'kb', 'event': 'down', 'key': out})

    def on_release(self, key):
        """ Запись отпущенной клавиши """
        try:
            out = key.char
        except:
            out = str(key)
            if key == keyboard.Key.space:
                # Обработка пробела отдельно
                out = ' '

        self.record.append({'type': 'kb', 'event': 'up', 'key': out})

    def on_click(self, x, y, button, is_pressed):
        """ Запись нажатия и отпускания кнопки мыши происходит,
        если определен объект на котором был клик """
        if not is_pressed:
            return  # Если кнопка отпущена, то ничего не записываем

        hash_element = screen.list_search(x, y)  # Поиск элемента на экране по координатам клика

        # -------------------------------
        # Сохранение изображений в отчете
        scr = ImageReport.circle_an_object(screen.screenshot, screen.hashes_elements.values())  # Обводим элементы
        self.report.save(scr, screen.get_element(hash_element))  # Сохранение скриншота и элемента
        # -------------------------------

        if not hash_element:
            # Если элемент не найден, то выходим
            return

        # Записываем перемещение мыши
        out = {'type': 'mouse', 'event': 'click', 'image': hash_element}
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


keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)  # Инициализация прослушивания клавиатуры
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

        if action['event'] == 'click':
            # Перемещение мыши к заданной позиции
            # Позиция определяется по центру элемента хэш которого указан в action['image']
            res = screen.get_hash_element(action['image'])
            if res:
                pyautogui.moveTo(*res, 0.3)
                pyautogui.click(*res, button='left')

            return

        # Подготовка к распознаванию как отдельных символов, так и специальных клавиш
        insert = action['key']
        if len(action['key']) == 1:
            insert = f"'{insert}'"

        if action['type'] == 'kb':
            # Работа с клавиатурой

            if action['event'] == 'down':
                # Нажатие клавиши
                exec(f"kb.press({insert})")
            else:
                # Отпускание клавиши
                sleep(self.duration)  # Удержание клавиши нажатой
                exec(f"kb.release({insert})")

                sleep(self.gap)  # Пауза между нажатиями и/или кликами

        else:
            # Ставим указатель мыши в нужную позицию
            mo.position = (action['x'], action['y'])

            # Нажатие и отпускание кнопки мыши
            if action['event'] == 'down':
                # Нажатие клавиши

                # Проверяем, есть ли нужный элемент под курсором и если нет,
                # пытаемся найти его на экране, ожидаем и повторяем попытку на случай долгого открытия приложения
                rep = 3
                while rep:

                    try:
                        x = action['x']
                        y = action['y']
                        # x, y = pattern_search(action['image'], x, y)  # Поиск элемента на экране
                        mo.position = (x, y)
                        self.button_up[action['key']] = (x, y)  # Координаты отпускания для левой или правой клавиш мыши
                        exec(f"mo.press({insert})")
                        rep = 0

                    # Ошибки при поиске элемента
                    except TemplateNotFoundError as err:
                        print(err)
                        raise

                    except ElementNotFound as err:
                        print(err, 'Ожидание приложения...')
                        sleep(1)
                        rep -= 1
                        if not rep:
                            print(err)
                            raise
            else:
                # Отпускание клавиши
                sleep(self.duration)  # Удержание клавиши нажатой

                if self.button_up[action['key']]:
                    # Координаты в которых должна быть отпущена клавиша мыши, запомнены, при ее нажатии
                    mo.position = self.button_up[action['key']]

                exec(f"mo.release({insert})")

                sleep(self.gap)  # Пауза между нажатиями и/или кликами


play = Play()  # Экземпляр проигрывателя
