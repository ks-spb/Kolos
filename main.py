""" Версия v4.
19.06.25 - Создал новый файл main. Отрабатывается алгоритм со слоями.
"""


import time
import sys
from time import sleep
import random
from multiprocessing import Process, Queue, Manager

from PIL.ImageStat import Global

import screen_monitoring
from db import Database
from mous_kb_record import rec, play
from screen_monitoring import process_changes
from screen import screen
from report import report


def stiranie_pamyati():
    global old_ekran
    # Удаление лишних строчек в таблице точки, где id>10 - это точка и реакция на 0, которая постоянно записывается.
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM points WHERE id > 3")
    cursor.execute("DELETE FROM svyazi WHERE ID > 3")
    cursor.execute("UPDATE points SET signal = 0 ")
    old_ekran = 0


def obrabotka_symbol(symbol):
    """Функция вводится в версии 4.
    Пришла буква:
    Находим наибольший сигнал из всех точек, пусть это Max.
    Создаем точку с именем 'n' и типом ‘in’ или обновляем ее сигнал n.signal = Max + 1.
    От предыдущей точки  к текущей создаем связь"""

    # Поиск максимального сигнала в таблице points
    max_signal = cursor.execute("SELECT MAX(signal) FROM points").fetchone()
    # print(f'Максимальный сигнал такой: {max_signal}')
    if max_signal is not None and max_signal[0] is not None:
        new_signal = max_signal[0] + 1
    else:
        new_signal = 1  # Значение по умолчанию
    # print(f'А теперь максимальный сигнал такой: {max_signal}')

    # поиск точки с самым большим сигналом, чтобы с ней построить связь
    nayti_id_max_signal = cursor.execute("SELECT id FROM points WHERE signal = ?", (max_signal)).fetchone()
    print(f'obrabotka_symbol. Найдена точка с максимальным сигналом: {nayti_id_max_signal}')

    # print(f'obrabotka_symbol. Передано на обработку следующее: {symbol}')
    nayti_id = cursor.execute("SELECT id FROM points WHERE name = ?", (symbol,)).fetchone()
    # print("obrabotka_symbol. id у входящей точки такой: ", nayti_id)
    if not nayti_id:
        # если такой точки нет - то создаётся новая с самым большим сигналом
        # print("obrabotka_symbol. Такого id нету")
        new_tochka_name = sozdat_new_tochky(symbol, 'in', new_signal)
        print(f"Создали новую точку in id: {new_tochka_name}")
    else:
        # Если такая точка имеется - то обновляется её сигнал: Max+ 1
        new_tochka_name = nayti_id[0]
        cursor.execute("UPDATE points SET signal = ? WHERE id = ?", (new_signal, new_tochka_name))

    sozdat_svyaz(nayti_id_max_signal[0], new_tochka_name)
    online_svyaz(new_tochka_name)


def sozdat_svyaz(id_start, id_finish):
    # Создаётся связь между двумя точками. В v4 нет проверки имеется ли связь или нет. Создаётся много связей. И может
    # создаваться закольцованная связь.
    max_id_svyazi = tuple(cursor.execute("SELECT MAX(id) FROM svyazi"))
    for max_id_svyazi1 in max_id_svyazi:
        old_id_svyazi = max_id_svyazi1[0]
        new_id_svyazi = old_id_svyazi + 1
    print(f'Создана связь м/у id_start = {id_start} и id_finish {id_finish}')
    cursor.execute("INSERT INTO svyazi VALUES (?, ?, ?)", (new_id_svyazi, id_start, id_finish))


def sozdat_new_tochky(name, type, signal):
    max_id = cursor.execute("SELECT MAX(id) FROM points").fetchone()
    new_id = max_id[0] + 1
    cursor.execute("INSERT INTO points VALUES (?, ?, ?, ?)", (new_id, name, type, signal))
    return new_id


def online_svyaz(tochka):
    # Функция, которая помогает находить последовательность действий ранее вводимых точек. Т.е. если было введено
    # "new age", а затем заново вводится "new" - то программа предположит, что скорее всего дальше будет " age".
    # Алгоритм:
    # * Найти все связи с точками, где текущая точка с сигналом max является start
    # * Проверить - если ID связи увеличивается на +1 - записать новое значение ID связи в начало списка,
    # удалить из найденного списка
    # * Удалить все ненайденые ID связи, которые были записаны до этого
    # * Добавить новые ID связей в конец списка по убыванию значения
    global online_svyaz_list
    print(f"online_svyaz. Изначально имеется следующий список online_svyaz_list: {online_svyaz_list} и передаётся точка :"
          f"{tochka} ************************")
    poisk_svyazi = cursor.execute("SELECT ID FROM svyazi WHERE id_start = ?", (tochka,)).fetchall()
    print(f'online_svyaz. С точкой: {tochka} найдены ID связей: {poisk_svyazi}')
    spisok = [row[0] for row in poisk_svyazi]
    # Прорабатываем список:
    # 1. Проходим по каждому элементу списка online_svyaz_list
    # 2. Если находится значение равное +1 в новом списке poisk_svyazi - то заменяется текущее значение на это новое и
    # удаляем его из poisk_svyazi
    # 3. Если не находим - удаляем текущее значение из online_svyaz_list
    # 4. В конце добавляем оставшиеся значения из poisk_svyazi в online_svyaz_list
    # Проходим по значениям списка online_svyaz
    i = 0
    while i < len(online_svyaz_list):
        current_value = online_svyaz_list[i]

        # Проверяем, есть ли в spisok значение, равное current_value + 1
        if (current_value + 1) in spisok:
            # Если есть, заменяем текущее значение на следующее из spisok
            next_value = current_value + 1
            online_svyaz_list[i] = next_value

            # Удаляем это значение из spisok
            spisok.remove(next_value)
        else:
            # Если такого значения нет, просто удаляем текущее значение
            online_svyaz_list.pop(i)
            continue  # Продолжаем с тем же индексом

        # Увеличиваем индекс только если значение не было удалено
        i += 1

    # Добавляем оставшиеся значения из spisok в конец online_svyaz
    online_svyaz_list.extend(spisok)

    print(f'В итоге получился следующий список онлайн связей: {online_svyaz_list} ***********************')



def proshivka():
    # Логика:
    # 1. Если есть уже собранный ранее путь:
    #   a. Пропустить эту функцию
    # 2. Если список pamyat пустой - пропустить эту функцию
    # 3. Иначе:
    #   a. Берётся онлайн связь первая в списке
    #   b. Найти ID точки по связи, указанной в списке Online_svyaz
    #   c. Проверяется находится ли эта точка в списке отрицательных действий
    #       i. если находится и эта точка первая в списке путь - то удалить онлайн связь и перейти к пункту 3.а
    #   d. Если не находится в списке отрицательных действий - записать в список “путь”, эту точку и ID связи
    #   e. Ищется следующая точка от этой добавленной, при этом ID связи увеличивается на 1 от только что добавленной
    #   f. Добавляется в путь найденный ID связи и найденная точка по этой связи
    #   g. Повтор от пункта “f” пока не произойдёт следующее:
    #       i. не закончатся связи с ID +1
    #           1. Совершить действие, находящееся в первом пункте списка Путь -> запустить функцию out_red(text)
    #       ii. не будет добавлена в путь точка с типом реакция
    #           1. Если была добавлена положительная или нейтральная реакция в путь - применить первое действие в списке Путь -> запустить функцию out_red(text)
    #           2. Если была добавлена отрицательная реакция в путь -
    #               a. добавить предыдущую точку в список отрицательных действий. Т.е. в список отрицательных действий добавляется та точка, которая ведёт к отрицательной реакции
    #               b. удалить этот путь
    #               c. Удалить первый пункт из списка онлайн связей
    #               d. Запустить функцию прошивку заново с пункта 3a

    print("Работа функции proshivka********************************************")
    global in_pamyat_name
    global pyt
    global online_svyaz_list
    global spisok_otricatelnih_deystvii
    # 1. Если есть уже собранный ранее путь - пропустить эту функцию
    print(f'Передаётся следующий путь: {pyt}')
    if pyt:
        out_red(pyt[0][0])   # Первое действие в пути
        pyt.pop(0)
        return
    # 2. Если список pamyat пустой - пропустить эту функцию
    print(f'Передаётся следующий in_pamyat_name: {in_pamyat_name}')
    if not in_pamyat_name:
        return
    # 3. Иначе:
    #   a. Берётся онлайн связь первая в списке
    if online_svyaz_list:
        pervaya_online_svyaz = online_svyaz_list[0]
        print(f'Первая точка в списке онлайн связей: {pervaya_online_svyaz}')
        #   b. Найти ID точки по связи, указанной в списке Online_svyaz
        id_tochki_online_svyazi = cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?",
                                                 (pervaya_online_svyaz, )).fetchone()
        print(f'Нашли id_finish: {id_tochki_online_svyazi} от первой в списке онлайн связей')
        # c. Проверяется находится ли эта точка в списке отрицательных действий
        if id_tochki_online_svyazi[0] in spisok_otricatelnih_deystvii:
            if pyt[0][0] ==  id_tochki_online_svyazi[0]:   # Если точка первая в пути
                online_svyaz_list.pop(0)   # удаляется первое значение в списке онлайн путь
        # Проверка является ли найденная точка реакцией
        elif id_tochki_online_svyazi[0] in (1, 2, 3):
            print('Найденная точка является реакцией - поэтому вышли из функции')
            in_pamyat_name = []   # Обнулить список памяти - т.к. цепочка дошла до нужного результата
            print("\033[0m {}".format("**********************************"))
            print("\033[31m {}".format("Был пройден весь путь и цепочка действий закончилась"))  # Ответ
            print("\033[0m {}".format("**********************************"))
            return
        #   d. Если не находится в списке отрицательных действий - записать в список “путь”, эту точку и ID связи
        pyt.append((id_tochki_online_svyazi[0], pervaya_online_svyaz))

        #   e. Ищется следующая точка от этой добавленной, при этом ID связи увеличивается на 1 от только что добавленной
        next_id = pervaya_online_svyaz + 1
        print(f'next_id стал: {next_id}')
        while True:
            # Т.е. id связи стал равен +1 от первоначальной. Найдём id_finish этой связи
            next_point = cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?", (next_id, )).fetchone()
            print(f'Нашли id точки {next_point} от +1 к первой онлайн связи: {next_id}')
            if next_point is None:
                # Если не нашли такую точку (значит закончились связи) - то выходим из цикла
                break

            # Проверка на тип точки - является ли реакцией REAC при этом сразу проверяем является ли положительной "poz"
            # или отрицательной "neg" или нейтральной "ney"
            type_tochki = cursor.execute("SELECT name FROM points WHERE ID = ?", next_point).fetchone()
            print(f'Нашли следующий name точки: {type_tochki[0]} у id = {next_point}')
            if type_tochki[0] in ('ney', 'poz'):
                print("Следующая точка нейтральная или положительная реакция")
                # Если следующая точка нейтральная или положительная реакция - то выходим из цикла
                break
            elif type_tochki[0] == 'neg':
                print(f'В список отрицательных действий добавлена предыдущая точка - т.е. которая первая в списке онлайн'
                      f'связей: {pervaya_online_svyaz}')
                spisok_otricatelnih_deystvii.append(pervaya_online_svyaz)
                pyt.clear()   #Удаляется путь
                online_svyaz_list.pop()   # Удаляем первый пункт из списка онлайн связей


            pyt.append((next_point[0], next_id))   # В путь добавляется найденная точка и ID связи

            next_id = next_id + 1

            # совершается действие из первого пункта списка путь
            print(f'Путь стал таким: {pyt}')
        if pyt:
            print(f'Совершается действие из первого пункта списка путь: {pyt}')
            out_red(pyt[0][0])
            pyt.pop(0)   # Удаляется первая часть пути (первый индекс)
        # здесь может собираться несколько путей, а затем выбираться лучший из них


def out_red(id):
    # Воспроизведение событий клавиатуры и мыши.
    # Данные в 1 списке, подряд для всех событий:
    # Для клавиатуры 2 элемента: 'Key.down'/'Key.up', Клавиша (символ или название)
    # Для сочетаний клавиш, 'Key.hotkey', Название или id сочетания
    # Для мыши 4 элемента: 'Button.down'/'Button.up', 'left'/'right', 'x.y',  'image' (имя изображения элемента)
    # Пример: ['Button.down', 'left', 'elem_230307_144451.png', 'Button.up', 'left', 'Button.down',
    # 'left', 'elem_230228_163525.png', 'Button.up', 'left']
    # Для клика мыши сейчас только: 'click.image' (image - хэш элемента)
    global pyt
    global in_pamyat_name
    # Если первая точка в списке - реакция:
        # Создать связь от точки с max сигналом к нейтральной точке
        # Поменять сигнал нейтральной точки на max+1
        # Удалить список pamyat
    print(f'в out_red передалась следующее id: {id}')
    type_tochki = cursor.execute("SELECT type FROM points WHERE id = ?", (id, )).fetchone()
    print(f'out_red. Нашли следующий тип точки: {type_tochki[0]} у id = {id}')
    if type_tochki[0] == 'REAC':
        sozdat_svyaz(id, (3, ))
        # Поиск максимального сигнала в таблице points
        max_signal = cursor.execute("SELECT MAX(signal) FROM points").fetchone()
        cursor.execute("UPDATE points SET signal = ? WHERE id = 3", max_signal + 1)
        pyt = []
        in_pamyat_name = []

    else:
        print(f'Для ответа используется следующая точка: {id}')
        text = (cursor.execute("SELECT name FROM points WHERE id = (?)", (id, ))).fetchone()
        print(f"Такой приходит текст для ответа: {text}")
        print("\033[0m {}".format("**********************************"))
        print("\033[31m {}".format("Ответ программы:"))  # Ответ
        print("\033[31m {}".format(text[0]))   # Ответ
        print("\033[0m {}".format("**********************************"))
        i = 0
        while i < len(text):

            if '.' in text[i]:
                item = text[i].split('.')
                # print(f'Преобразовали текст в item: {item}')
                if item[0] == 'Key':
                    # Читаем и готовим событие для клавиатуры
                    event = {'type': 'kb'}
                    event['event'] = item[1]
                    event['key'] = text[i+1]
                    i += 2

                elif item[0] == 'Button':
                    # Читаем и готовим событие для мыши
                    event = {'type': 'mouse'}
                    event['event'] = item[1]
                    # print(f'event такой 1: {event}')
                    print(f'i сейчас такой = {i}')
                    event['key'] = 'Button.' + item[1]
                    print(f'event такой 2: {event}')

                elif item[0] == 'click':
                    event = {'type': 'mouse', 'event': 'click', 'image': item[1]}

                    # Закомментировал - т.к. дальше происходит добавление в команду координат x и y

                    # print(f"В х и у передаётся следующее: {text[i+2]}")
                    # x, y = text[i+2].split('.')
                    # if event['event'] == 'down':
                    #     event['image'] = text[i + 3]
                    #     i += 1
                    # i += 3  # У событий вверх и вниз разная длина, поэтому счетчик увеличиваем соответственно
                    # event['x'] = int(x)
                    # event['y'] = int(y)

                elif item[0] == 'position':
                    # Данные для перемещения мыши без кликов
                    event = {'type': 'mouse', 'event': 'move', 'x': item[1], 'y': item[2]}

                else:
                    i += 1
                    continue
                try:
                    play.play_one(event)  # Воспроизводим событие
                except:
                    # print('Выполнение скрипта остановлено')
                    break

                continue

            elif text[i] == 'click':
                event = {'type': 'mouse', 'event': 'click', 'image': text[i+1]}

                # -------------------------------
                # Сохранение изображений в отчете
                report.set_folder('out_red')  # Инициализация папки для сохранения изображений
                # -------------------------------

                i += 1
                try:
                    play.play_one(event)  # Воспроизводим событие
                except:
                    print('Выполнение скрипта остановлено')
                    break

                continue

            i += 1

        # Обновить сигнал у 1й точки в пути = max+1
        # Создать связь от предыдущей точки с max-1 к этой точке
        # Запустить функцию online_svyaz
        max_signal = cursor.execute("SELECT MAX(signal) FROM points").fetchone()
        # print(f'Максимальный сигнал сейчас такой: {max_signal}')
        poisk_predidushego_max_signal = poisk_id_s_max_signal_points()
        cursor.execute("UPDATE points SET signal = ? WHERE id = ?", (max_signal[0] + 1, id))
        print(f'Создаётся связь от {poisk_predidushego_max_signal} к {id}')
        sozdat_svyaz(poisk_predidushego_max_signal, id)
        online_svyaz(id)


def poisk_id_s_max_signal_points():
    max_signal = cursor.execute("SELECT MAX(signal) FROM points").fetchone()
    poisk_id_max_signal = cursor.execute("SELECT id FROM points WHERE signal = ?", max_signal).fetchone()
    return poisk_id_max_signal[0]


def tekyshiy_ekran():
    # Находится id текущего экрана.
    id_ekran = screen.screenshot_hash
    new_name_id_ekran = "id_ekran_" + str(id_ekran)
    # print(f'Новый нейм экрана: {new_name_id_ekran}')
    poisk_id_ekrana = cursor.execute("SELECT id FROM points WHERE name = ?", (new_name_id_ekran,)).fetchone()
    if poisk_id_ekrana:
        for poisk_id_ekrana1 in poisk_id_ekrana:
            id_tekushiy_ekran = poisk_id_ekrana1
            # print(f'Текущий экран: {id_tekushiy_ekran}')
        return id_tekushiy_ekran


def perenos_sostoyaniya():
    # Функция определяет какой сейчас экран, отличается ли от старого. Если отличается - перенос posl_t0 в этот экран
    global old_ekran
    id_screen, hash_string = queue_hashes.get()  # Получаем id_screen и хэш из очереди
    # print(f'id_screen2 = {id_screen[1]}')
    new_name_id_ekran = "id_ekran_" + str(id_screen[1])
    print(f'Новый нейм экрана в перенос состояния: {new_name_id_ekran}')
    obrabotka_symbol(new_name_id_ekran)
    print(f"Сейчас такой экран id: {new_name_id_ekran}, старый экран такой: {old_ekran}")
    if old_ekran != new_name_id_ekran:
        old_ekran = new_name_id_ekran
        print(f'Теперь старый и новый экраны одинаковые')
    # else:
        # print('!!!!!!!!!!!!!ВНИМАНИЕ!!!!!!ЭКРАН НЕ ИЗМЕНИЛСЯ!!!!!!!!!!!')


if __name__ == '__main__':
    old_ekran = 0
    # Запуск процесса наблюдения за экраном
    print('Запуск процесса наблюдения за экраном')
    manager = Manager()  # Управление доступом к общим объектам
    queue_hashes = manager.Queue()  # Очередь для передачи списка хэшей элементов
    queue_img = Queue()  # Очередь для передачи скриншота в np
    p1 = Process(name='ElementSearch', target=process_changes, args=(queue_hashes, queue_img,))
    p1.start()

    screen.queue_hashes = queue_hashes  # Передаем источник экранов в их приемник в основном потоке

    # -----------------------------------------------------------
    cursor = Database('Li_db_v1_4.db')
    A = True

    t0_10 = 0  # для проверки на изменение to за 10 циклов

    source = 'input'  # Получает значение источника ввода None - клавиатура (None запустит автоматический переход по
    # циклам, 'rec' -  запись клавиатуры и мыши, 'input' - ручное переключение
    last_update_screen = 0  # Время последнего обновления экрана
    schetchik = 0
    most_new = 0
    online_svyaz_list = []
    time.sleep(1.0)

    in_pamyat = []  # 20.12.23 - Список для хранения входящих id (in)
    in_pamyat_name = []  # 12.01.24 - Список для хранения входящих в виде name, а не id
    spisok_otricatelnih_deystvii = []   # Список отрицательных действий, которые не должна совершать программа при
    # выполнении одной задачи

    pyt = []   # Путь, который собирается во время работы функции proshivka
    zolotoy_pyt = []  # 19.01.24 - Путь, являющийся самым коротким для достижения положительного результата
    izmenilos_li_sostyanie = 0


    perenos_sostoyaniya()

    while A:
        if rec.status:
            # Блокируем основную программу, пока идет запись
            sleep(0.001)
            continue

        # -------------------------------------------------------
        # Активация и деактивация точек в соответствии с экраном
        # -------------------------------------------------------
        # if screen.last_update != last_update_screen:
        screen.get_screen()
        scrsh = screen.screenshot
        # if scrsh is not None:
        #     # -------------------------------
        #     # Сохранение изображений в отчете
        #     report.set_folder('update_points')  # Инициализация папки для сохранения изображений
        #     scr = report.circle_an_object(scrsh, screen.hashes_elements.values())  # Обводим элементы
        #     report.save(scr)  # Сохранение скриншота и элемента
            # -------------------------------

        # zazhiganie_obiektov_na_ekrane()   # TODO вернуть в работу это зажигаение?

        schetchik += 1
        print('************************************************************************')
        print("schetchik = ", schetchik)


        if not queue_hashes.empty():
            print("Изменился экран - поэтому запускается функция переноса состояния")
            perenos_sostoyaniya()

        if source == 'input':
            # Ввод строки с клавиатуры, запись по-буквенно
            vvedeno_luboe = input("Введите текст: ")

        elif source == 'rec':
            # Источник события мыши и клавиатуры. Чтение из объекта rec
            # Формат записи
            # Для клавиатуры: 'Key.down'/'Key.up', Клавиша (символ или название)
            # При сохранении сочетаний клавиш, 'Key.hotkey', Название или id сочетания
            # Для мыши: 'Button.down'/'Button.up', 'left'/'right', 'x.y', 'image' (имя изображения элемента)
            # Для мыши: 'click.image' (image - хэш элемента)

            vvedeno_luboe = []
            source = None
            n = 0

            for event in rec.record:

                if event['type'] == 'kb':
                    # Запись события клавиатуры
                    vvedeno_luboe.append('Key.' + event['event'])
                    vvedeno_luboe.append(event['key'])

                else:
                    # Запись события мыши
                    # position.x.y, image.id, Button.up.left,
                    print(f'Передаются на запись следующие event: {event}')
                    if event['event'] == 'click':
                        vvedeno_luboe.append('position.' + str(event['x']) + '.' + str(event['y']))
                        if event['image'] is not None:
                            vvedeno_luboe.append('click.' + event['image'])
                        else:
                            vvedeno_luboe.append('click.')
                    #     vvedeno_luboe.append('image.' + str(event['image']))
                    # vvedeno_luboe.append('Button.' + event['event'] + '.' + event['key'].split('.')[1])

                n += 1

            print(vvedeno_luboe, '---------------------------------------------------')
            if n:
                print(f'Сохраненo {n} записанных событий', end='\n\n')
            else:
                print('Нет событий для записи', end='\n\n')

        else:

            if rec.key_down in '0123459':
                vvedeno_luboe = rec.key_down
            elif rec.key_down == 'Key.space':
                source = 'input'
                vvedeno_luboe = ''
            rec.key_down = ''
            sleep(0.5)
        print("")

        if vvedeno_luboe in [' 0', '0']:
            tree = ()
            A = False
            in_pamyat = []
            # cursor.execute("UPDATE points SET puls = 0 AND signal = 0 AND work = 0")
            old_ekran = 0
            online_svyaz_list = []
            spisok_otricatelnih_deystvii = []
            print('!!!Отработана функция 0 !!! Обнуляется онлайн связь и список отрицательных действий')
            continue

        elif vvedeno_luboe in [' 1', '1']:
            """ Создаётся связь м/у положительной реакцией и текущим состоянием (точкой с наибольшим сигналом). 
                При вводе - стирается первый введённый элемент задания (памяти) и состояние переводится 
                на текущий экран."""

            tekushiy_id = poisk_id_s_max_signal_points()
            obrabotka_symbol(1)   # Положительная реакция будет отработана как символ
            # sozdat_svyaz(tekushiy_id, 1)

            source = 'input'   # Было None и включался автопереход по циклам
            vvedeno_luboe = ''

            schetchik = 0  # 12.09.23 Добавил переход к началу цикла, если была применена реакция

            # print(f'in_pamyat перед удалением первого элемента: {in_pamyat}')
            in_pamyat_name = []
            in_pamyat = []
            # if in_pamyat:
            #     in_pamyat.pop(0)
            #     print(f'Удалён первый элемент из in_pamyat, теперь список такой: {in_pamyat}')
            # if in_pamyat_name:
            #     in_pamyat_name.pop(0)
            #     print(f'Удалён первый элемент из in_pamyat_name, теперь список такой: {in_pamyat_name}')
            perenos_sostoyaniya()   #Переносится состояние на текущий экран

        elif vvedeno_luboe in [' 2', '2']:
            # Введена отрицательная реакция - создать с ней связь

            source = 'input'
            vvedeno_luboe = ''

            # Ищется точка с максимальным сигналом, которая была введена последней
            tekushiy_id = poisk_id_s_max_signal_points()
            # Создаётся связь с отрицательной реакцией
            sozdat_svyaz(tekushiy_id, 1)
            # Действие добавляется в список отрицательных действий
            spisok_otricatelnih_deystvii.append(tekushiy_id)
            # сигнал текущей точки обнуляется, чтобы её не повторять - т.е. система откатится на шаг назад
            cursor.execute("UPDATE points SET signal = 0 WHERE id = ?", (tekushiy_id, ))
            # путь обнулится
            pyt = []


            # if in_pamyat != 0:
            #     # После отрицательной реакции - состояние переносится к предыдущей t0, которая не является кликом
            #     # (т.е. name2 менее 16 знаков)
            #     poisk_t0_dlya_otkata = True
            #     posl_t0_dlya_cicla = posledniy_t_0
            #     # Удаление связи моста и этой t0 - т.к. она не ведёт к (+)
            #     while poisk_t0_dlya_otkata:
            #         # предыдущий t0 прописан в rod1 - найти эту точку
            #         poisk_predidushego_t0 = cursor.execute("SELECT rod1 FROM points WHERE id = ?",
            #                                                (posl_t0_dlya_cicla,)).fetchall()
            #         # проверить какой длины name2 - если 16 знаков - то это клик и искать следующую t0
            #         for poisk_predidushego_t01 in poisk_predidushego_t0:
            #             proverka_name2 = cursor.execute("SELECT name2 FROM points WHERE id = ? "
            #                                             "AND LENGTH(name2) < 16", poisk_predidushego_t01).fetchall()
            #             # Если такая точка найдена - то это искомый t0 к нему и переходим
            #             if proverka_name2:
            #                 posledniy_t_0 = poisk_predidushego_t01[0]
            #                 poisk_t0_dlya_otkata = False
            #                 print(f'Состояние после получения (-) реакции было перенесено в t0: {posledniy_t_0}. '
            #                       f'До этого был posl_t0: {posl_t0_dlya_cicla}')
            #             else:
            #                 # Если name2 у этой t0 = 16 - то это клик - значит ищем следующую
            #                 posl_t0_dlya_cicla = poisk_predidushego_t01[0]

        elif vvedeno_luboe in [' 3', '3']:
            # Включение записи
            cursor.commit()  # Сохраняем изменения в БД
            sleep(0.5)
            rec.start()
            # source = None  # Запись сохранится в месте ввода
            continue

        elif vvedeno_luboe in [' 4', '4']:
            # Показать запись3
            sleep(0.5)

            # -------------------------------
            # Сохранение изображений в отчете
            report.set_folder('play_4')  # Инициализация папки для сохранения изображений
            # -------------------------------

            for i in rec.record:
                print(i)
                try:
                    play.play_one(i)
                except:
                    print('Выполнение скрипта остановлено')
                    break
            source = None
            vvedeno_luboe = ''
            continue

        elif vvedeno_luboe in [' 5', '5']:
            # Сохранение записи
            source = 'rec'  # Запись сохранится в месте ввода
            vvedeno_luboe = ''
            # continue

        elif vvedeno_luboe in [' 6', '6']:
            # Сброс состояния
            print("Сброс состояния до текущего экрана")
            schetchik = 0

        elif vvedeno_luboe in [' 7', '7']:
            print("Стирание краткосрочной памяти")
            in_pamyat = []
            in_pamyat_name = []

        elif vvedeno_luboe in [' 8', '8']:
            # запуск автоматического срабатывания счётчика без нажатия enter
            source = None   # Если поставить 'input' - то будет ручной переход по циклам

        elif vvedeno_luboe in [' 9', '9']:
            stiranie_pamyati()
            # source = None
            vvedeno_luboe = ''
            schetchik = 0
            in_pamyat = []
            in_pamyat_name = []

        elif vvedeno_luboe != "":
            bil_klick = False
            print(vvedeno_luboe, '========================= Введено')
            for vvedeno_luboe1 in vvedeno_luboe:
                # 16.06.23 - связываем сущность одной команды с t0, обнуляем tp и t
                # print(f"Рассматривается следующее введённое сообщение: {vvedeno_luboe1}")
                if '.' and 'click' in vvedeno_luboe1:
                    # print(f"Сообщение содержит и точку и click: {vvedeno_luboe1}")
                    # для разрыва сущности, если происходит нажатие кнопок, а затем клик мышкой
                    # Если клик не находится в начале списка - нужно принудительно отделить его от предыдущих сущностей
                    for vvedeno_luboe2 in vvedeno_luboe1.split('.'):
                        obrabotka_symbol(vvedeno_luboe2)
                    bil_klick = True
                else:
                    # print(f'Сообщение не содержит точку или click: {vvedeno_luboe1}')
                    obrabotka_symbol(vvedeno_luboe1)
                    bil_klick = False
            # 12.01.23 - Если введено не list (т.е. не содержит клик) - то сохранить во входящих
            # print(f'vvedeno_luboe = {vvedeno_luboe}')
            if not isinstance(vvedeno_luboe, list):
                for vvedeno_luboe_split in vvedeno_luboe.split():
                    print(f"Добавляется в in_pamyat_name {vvedeno_luboe_split}")
                    in_pamyat_name.append(vvedeno_luboe_split)
            print(f'in_pamyat_name содержит следующее: {in_pamyat_name}')
            vvedeno_luboe = ''
            # print("Было введено vvedeno_luboe: ", vvedeno_luboe)
            # schetchik = 0   # 07.11.23 - добавлено обнуление, чтобы не перешло состояние к старому экрану
            source = 'input'
        else:
            if schetchik == 1:
                print(f'Счетчик = 1 и in_pamyat сейчас такая: {in_pamyat_name}')
                if in_pamyat_name != []:
                    # Если программа сюда перешла - значит не было ничего введено и происходит поиск возможных действий.
                    proshivka()
            elif schetchik >= 10:
                schetchik = 0

    p1.terminate()