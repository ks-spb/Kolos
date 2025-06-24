""" Версия v4.
19.06.25 - Создал новый файл main. Отрабатывается алгоритм со слоями.
"""


import time
import sys
from time import sleep
import random
from multiprocessing import Process, Queue, Manager

from PIL.ImageStat import Global

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
    """Функция вводится в версии 4. Вместо obrabotka_symbol.

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
          f"{tochka}")
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

    print(f'В итоге получился следующий список онлайн связей: {online_svyaz_list}')



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


    global in_pamyat_name
    global pyt
    global online_svyaz_list
    global spisok_otricatelnih_deystvii
    # 1. Если есть уже собранный ранее путь - пропустить эту функцию
    if pyt:
        return
    # 2. Если список pamyat пустой - пропустить эту функцию
    if not in_pamyat_name:
        return
    # 3. Иначе:
    #   a. Берётся онлайн связь первая в списке
    pervaya_online_svyaz = online_svyaz_list[0]
    print(f'Первая точка в списке онлайн связей: {pervaya_online_svyaz}')
    #   b. Найти ID точки по связи, указанной в списке Online_svyaz
    id_tochki_online_svyazi = cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?",
                                             (pervaya_online_svyaz)).fetchone()
    print(f'Нашли id_finish: {id_tochki_online_svyazi} от первой в списке онлайн связей')
    # c. Проверяется находится ли эта точка в списке отрицательных действий
    if id_tochki_online_svyazi[0] in spisok_otricatelnih_deystvii:
        if pyt[0][0] ==  id_tochki_online_svyazi[0]:   # Если точка первая в пути
            online_svyaz_list.pop(0)   # удаляется первое значение в списке онлайн путь
            proshivka()   # снова проверяем следующую точку (переходим к пункту 3.а)

    #   d. Если не находится в списке отрицательных действий - записать в список “путь”, эту точку и ID связи
    pyt.append((id_tochki_online_svyazi[0], pervaya_online_svyaz))

    #   e. Ищется следующая точка от этой добавленной, при этом ID связи увеличивается на 1 от только что добавленной
    next_id = pervaya_online_svyaz + 1
    while True:
        # Т.е. id связи стал равен +1 от первоначальной. Найдём id_finish этой связи
        next_point = cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?", next_id).fetchone()
        print(f'Нашли id точки {next_point[0]} от +1 к первой онлайн связи: {next_id}')
        if next_point is None:
            # Если не нашли такую точку (значит закончились связи) - то выходим из цикла
            break

        # Проверка на тип точки - является ли реакцией REAC при этом сразу проверяем является ли положительной "poz"
        # или отрицательной "neg" или нейтральной "ney"
        type_tochki = cursor.execute("SELECT name FROM tochki WHERE ID = ?", next_point[0]).fetchone()
        print(f'Нашли следующий тип точки: {type_tochki[0]} у id = {next_point[0]}')
        if type_tochki[0] in (('ney', ), ('poz', )):
            print('Совершается действие при следующей положительной или отрицательной реакцией')
            # Если следующая точка нейтральная или положительная реакция - то выходим из цикла
            break
        elif type_tochki[0] == ('neg',):
            print(f'В список отрицательных действий добавлена предыдущая точка - т.е. которая первая в списке онлайн'
                  f'связей: {pervaya_online_svyaz}')
            spisok_otricatelnih_deystvii.append(pervaya_online_svyaz)
            pyt.clear()   #Удаляется путь
            online_svyaz_list.pop()   # Удаляем первый пункт из списка онлайн связей


        pyt.append((next_point, next_id))   # В путь добавляется найденная точка и ID связи

        # совершается действие из первого пункта списка путь
        print(f'Здесь должно совершиться действие из первого пункта списка путь')





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
    # циклам, 'rec' -  запись клавиатуры и мыши
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

    while A:
        schetchik += 1
        print('************************************************************************')
        # print("schetchik = ", schetchik, "     Экран", screen.screenshot_hash)
        print("schetchik = ", schetchik)

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
                            vvedeno_luboe.append(
                                'click.')  # todo внедрить отличие в клике по пустым объектам (добавить дополнительные поля в определение изображения)
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
            posledniy_t = 0
            posledniy_tp = 0
            old_ekran = 0
            posledniy_t_0 = 0
            # print('!!!Отработана функция 0 !!!')
            continue

        elif vvedeno_luboe in [' 1', '1']:
            """Создаётся связь м/у положительной реакцией и текущим состоянием. При вводе - стирается первый введённый 
             элемент задания (памяти) и состояние переводится на текущий экран."""
            # Нужно проверить имеется ли уже связь м/у t0 и tp
            # 06.02.24 - Не должна создаваться связь между экраном и положительной реакцией. Нужно проверить - если у
            # posl_t0 нет связи с tp - то найти предыдущий t0 и проверить у него.
            # Предыдущая t0 записана в rod1, а вот наличие связи с tp придётся проверить вручную.
            C = True
            t0_dlya_poiska_tp = posledniy_t_0
            while C:
                poisk_svyazi_s_tp = cursor.execute("SELECT svyazi.id_finish FROM svyazi JOIN points "
                                                   "ON svyazi.id_finish = points.id "
                                                   "WHERE svyazi.id_start = ? AND name = 'time_p' ",
                                                   (t0_dlya_poiska_tp,)).fetchone()
                if poisk_svyazi_s_tp:
                    for poisk_svyazi_s_tp1 in poisk_svyazi_s_tp:
                        # Связь с tp имеется - значит создаётся связь с этим t0 и выход из цикла
                        sozdat_svyaz(t0_dlya_poiska_tp, 1, 1)
                        print("Состояние перед (+) реакцией было такое: ", t0_dlya_poiska_tp,
                              ". С ней и создаётся связь")
                        C = False
                else:
                    # Связь с tp не имеется - значит ищется предыдущий t0 и проверяется связь с tp у него.
                    poisk_predidushego_t0_dlya_perehoda = cursor.execute("SELECT rod1 FROM points WHERE id = ?",
                                                                         (t0_dlya_poiska_tp,)).fetchone()
                    for poisk_predidushego_t0_dlya_perehoda1 in poisk_predidushego_t0_dlya_perehoda:
                        t0_dlya_poiska_tp = poisk_predidushego_t0_dlya_perehoda1
            # source = None
            vvedeno_luboe = ''

            schetchik = 0  # 12.09.23 Добавил переход к началу цикла, если была применена реакция

            print(f'in_pamyat перед удалением первого элемента: {in_pamyat}')
            if in_pamyat:
                in_pamyat.pop(0)
                print(f'Удалён первый элемент из in_pamyat, теперь список такой: {in_pamyat}')
            if in_pamyat_name:
                in_pamyat_name.pop(0)
                print(f'Удалён первый элемент из in_pamyat_name, теперь список такой: {in_pamyat_name}')

        elif vvedeno_luboe in [' 2', '2']:
            # нужно проверить имеется ли уже связь м/у t0 и tp
            # 06.02.24 - Не должна создаваться связь между экраном и отрицательной реакцией. Нужно проверить - если у
            # posl_t0 нет связи с tp - то найти предыдущий t0 и проверить у него.
            C = True
            t0_dlya_poiska_tp = posledniy_t_0
            while C:
                poisk_svyazi_s_tp = cursor.execute("SELECT svyazi.id_finish FROM svyazi JOIN points "
                                                   "ON svyazi.id_finish = points.id "
                                                   "WHERE svyazi.id_start = ? AND name = 'time_p' ",
                                                   (t0_dlya_poiska_tp,)).fetchone()
                for poisk_svyazi_s_tp1 in poisk_svyazi_s_tp:
                    if poisk_svyazi_s_tp1:
                        # Связь с tp имеется - значит создаётся связь с этим t0 и выход из цикла
                        sozdat_svyaz(t0_dlya_poiska_tp, 2, 1)
                        print("Состояние перед (-) реакцией было такое: ", t0_dlya_poiska_tp,
                              ". С ней и создаётся связь")
                        C = False
                    else:
                        # Связь с tp не имеется - значит ищется предыдущий t0 и проверяется связь с tp у него.
                        poisk_predidushego_t0_dlya_perehoda = cursor.execute("SELECT rod1 FROM points WHERE id = ?",
                                                                             (t0_dlya_poiska_tp,)).fetchone()
                        for poisk_predidushego_t0_dlya_perehoda1 in poisk_predidushego_t0_dlya_perehoda:
                            t0_dlya_poiska_tp = poisk_predidushego_t0_dlya_perehoda1[0]
            source = None
            vvedeno_luboe = ''
            # schetchik = 0    # 12.09.23 Добавил переход к началу цикла, если была применена реакция
            posledniy_tp = 0
            posledniy_t = 0
            if in_pamyat != 0:
                # После отрицательной реакции - состояние переносится к предыдущей t0, которая не является кликом
                # (т.е. name2 менее 16 знаков)
                poisk_t0_dlya_otkata = True
                posl_t0_dlya_cicla = posledniy_t_0
                # Удаление связи моста и этой t0 - т.к. она не ведёт к (+)
                while poisk_t0_dlya_otkata:
                    # предыдущий t0 прописан в rod1 - найти эту точку
                    poisk_predidushego_t0 = cursor.execute("SELECT rod1 FROM points WHERE id = ?",
                                                           (posl_t0_dlya_cicla,)).fetchall()
                    # проверить какой длины name2 - если 16 знаков - то это клик и искать следующую t0
                    for poisk_predidushego_t01 in poisk_predidushego_t0:
                        proverka_name2 = cursor.execute("SELECT name2 FROM points WHERE id = ? "
                                                        "AND LENGTH(name2) < 16", poisk_predidushego_t01).fetchall()
                        # Если такая точка найдена - то это искомый t0 к нему и переходим
                        if proverka_name2:
                            posledniy_t_0 = poisk_predidushego_t01[0]
                            poisk_t0_dlya_otkata = False
                            print(f'Состояние после получения (-) реакции было перенесено в t0: {posledniy_t_0}. '
                                  f'До этого был posl_t0: {posl_t0_dlya_cicla}')
                        else:
                            # Если name2 у этой t0 = 16 - то это клик - значит ищем следующую
                            posl_t0_dlya_cicla = poisk_predidushego_t01[0]

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
            source = None

        elif vvedeno_luboe in [' 9', '9']:
            stiranie_pamyati()
            # source = None
            vvedeno_luboe = ''
            schetchik = 0

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
                    proshivka()
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
                # print(f'in_pamyat сейчас такая: {in_pamyat}')
                if in_pamyat != []:
                    # Вместо моста - зажечь повторно posl_t от первой (in)
                    # print(f'Зажигается повторно posl_t, первый в списке: {in_pamyat}')
                    # cursor.execute("UPDATE 'points' SET work = 1 WHERE id = ?", (in_pamyat[0],))
                    # 21.12.23 - за основу формирования дерева взята точка time, а не time_0
                    # Найти t от posl_t0
                    """Если программа сюда перешла - значит не было ничего введено и происходит поиск возможных действий.
                    Для поиска берётся точка t от последней t0"""
                    poisk_svyazi_t_i_t0 = tuple(cursor.execute("SELECT svyazi.id_start "
                                                               "FROM svyazi JOIN points "
                                                               "ON svyazi.id_start = points.id "
                                                               "WHERE svyazi.id_finish = ? AND points.name = 'time'",
                                                               (posledniy_t_0,)))
                    print(
                        f'Для последующей прошивки найдена следующая time: {poisk_svyazi_t_i_t0}, где posl_t0 = {posledniy_t_0}')

            elif schetchik >= 10:

                schetchik = 0


                # 28.11.23 - Если за 10 счётчиков не произошло никаких реакций, действий - то posl_t0 становится
                # old_ekran, а если произошло - продолжаются действия и posl_t0 не изменяется
                t0_10_proverka = posledniy_t_0
                print(f"Изменился ли t0? Текущий posl_t0 = {posledniy_t_0}, t0_proverka = posl_t0 = {t0_10_proverka}, "
                      f"старый t0 (в предыдущем 10м цикле) был = {t0_10}")
                if t0_10_proverka == t0_10:
                    if len(in_pamyat) == 0:
                        posledniy_t_0 = 0
                        posledniy_t = old_ekran
                        posledniy_t = 0
                        # posledniy_otvet = 0  # 07.11.23 - раньше последний ответ становился = 0, когда счётчик был = 1.
                        print("")
                        print(
                            ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                        print(
                            f">>>>>>>>>>>>>>>>>>>>  Переход в posl_t0 = {posledniy_t_0}  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                        print(
                            f">>>>>>>>>>>>>>>>>>>  Закончилась цепочка действий, началась новая  <<<<<<<<<<<<<<<<<<<<<<<")
                        print('')
                        print(
                            ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                else:
                    t0_10 = t0_10_proverka
                    print("")
                    print("-------------------Состояние posl_to поменялось-------------------------------")
                    print("-------------------Цепочка действий продолжается---------------------------------")
                    print("")

    p1.terminate()