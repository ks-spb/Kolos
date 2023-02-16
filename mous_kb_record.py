from time import sleep
from pynput import keyboard, mouse
from pynput.keyboard import Key, Controller as kb_Controller
from pynput.mouse import Button, Controller

kb = kb_Controller()
mo = Controller()

""" Вид в котором информация о событиях хранится объекте:
    
    Нажата клавиша 'A': {'type': 'kb', 'event': 'down', 'key': 'A'}
    Отпущена клавиша 'A': {'type': 'kb', 'event': 'up', 'key': 'A'}

    Нажата левая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.left', 'x': 671, 'y': 591}
    Нажата правая клавиша мыши: {'type': 'mouse', 'event': 'down', 'key': 'Button.right', 'x': 671, 'y': 591}
    Отпущена левая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.left', 'x': 671, 'y': 591}
    Отпущена правая клавиша мыши: {'type': 'mouse', 'event': 'up', 'key': 'Button.right', 'x': 671, 'y': 591}
"""


class Recorder:
    """ Прослушивание мыши и клавиатуры и запись событий с них """

    status = False  # Чтение с мыши и клавиатуры запрещено
    record = []  # В списке в порядке поступления хранятся события мыши и клавиатуры в виде кортежа словарей

    def start(self):
        """ Начать запись """
        self.record.clear()  # Удаление старой записи перед началом новой
        self.status = True

    def stop(self):
        """ Остановить запись """
        self.status = False

    def on_press(self, key):
        """ Запись нажатой клавиши """
        if key == keyboard.Key.esc:

            # Остановка записи по лавише Esc
            self.stop()
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
        """ Запись нажатия кнопки мыши клавиши """
        out = {'type': 'mouse'}
        out['event'] = 'down' if is_pressed else 'up'
        out['key'] = str(button)
        out['x'] = x
        out['y'] = y
        self.record.append(out)


rec = Recorder()  # Создаем объект записи


def on_press(key):
    """ Действие, когда пользователь нажимает клавишу на клавиатуре """

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

    gap = 0.5  # Промежуток между нажатиями клавиш и кликами мыши при воспроизведении (МС)
    duration = 0.001  # Длительность удержания кнопки нажатой (мыши и клавиатуры)

    def play_one(self, action):
        """ Воспроизведение одного действия """

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

        else:
            # Работа с мышью

            # Ставим указатель мыши в нужную позицию
            mo.position = (action['x'], action['y'])

            # Нажатие и отпускание кнопки мыши
            if action['event'] == 'down':
                # Нажатие клавиши
                exec(f"mo.press({insert})")
            else:
                # Отпускание клавиши
                sleep(self.duration)  # Удержание клавиши нажатой
                exec(f"mo.release({insert})")

        sleep(self.gap)  # Пауза между нажатиями и/или кликами


play = Play()  # Экземпляр проигрывателя

