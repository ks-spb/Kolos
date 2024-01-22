import time
import sys
from time import sleep
import random
from multiprocessing import Process, Queue, Manager

from db import Database
from mous_kb_record import rec, play
from screen_monitoring import process_changes
from screen import screen
from report import report




def stiranie_pamyati():
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp
    global old_ekran
    # Удаление лишних строчек в таблице точки, где ID>10 - это точка и реакция на 0, которая постоянно записывается.
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM tochki WHERE ID > 5")
    cursor.execute("DELETE FROM svyazi WHERE ID > 3")
    cursor.execute("UPDATE tochki SET puls = 0 AND signal = 0 AND work = 0")
    posledniy_t = 0
    posledniy_tp = 0
    old_ekran = 0
    posledniy_t_0 = 0


def poisk_bykvi_iz_vvedeno_v2(symbol):   # Функция находит ID у буквы из списка введённых
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp

    # print(f'Передано на обработку следующее: {symbol}')
    nayti_id = cursor.execute("SELECT ID FROM tochki WHERE name = ? AND type = 'mozg'", (symbol, )).fetchone()
    # print("poisk_bykvi_iz_vvedeno_v2. ID у входящей точки такой: ", nayti_id)
    if not nayti_id:
        # print("poisk_bykvi_iz_vvedeno_v2. Такого ID нету")
        new_tochka_name = sozdat_new_tochky(symbol, 0, 'mozg', 'zazech_sosedey', 1, 0, 10, 0, 0, symbol)
        # print("Создали новую точку in: ", new_tochka_name)
        new_tochka_print = sozdat_new_tochky(symbol, 0, 'print', "print1", 1, 0, 0, new_tochka_name, 0, symbol)
        new_tochka_time_t = sozdat_new_tochky('time', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                              posledniy_t, symbol)
        new_tochka_time_p = sozdat_new_tochky('time_p', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                            posledniy_tp, symbol)
        # нужно создать между ними связь
        sozdat_svyaz(new_tochka_name, new_tochka_time_t, 1)
        sozdat_svyaz(new_tochka_time_t, new_tochka_time_p, 1)
        sozdat_svyaz(new_tochka_time_p, new_tochka_print, 1)
        sozdat_svyaz(new_tochka_name, new_tochka_print, 1)  # 3.2.3 - эта связь нужна, чтобы создавалась сущность (tp)
        if posledniy_t != 0:
            sozdat_svyaz(posledniy_t, new_tochka_time_t, 1)  # weight was 0.1 in 2.3.1
        else:
            sozdat_svyaz(0, new_tochka_time_t, 1)
        posledniy_t = new_tochka_time_t
        # print(f"posledniy_t при вводе in стал равен = {posledniy_t}")
        if posledniy_tp != 0:
            # print('Создаётся новая связь posledniy_tp: ', posledniy_tp, ' и new_tochka_time_p: ', new_tochka_time_p)
            sozdat_svyaz(posledniy_tp, new_tochka_time_p, 1)
        posledniy_tp = new_tochka_time_p
    else:  # если есть такая буква с таким ID
        if nayti_id:
            cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_id)
            # print("Зажглась точка в проверке наличия точек: ", nayti_id)
            proverka_nalichiya_svyazey_in(nayti_id[0], symbol)



def proverka_nalichiya_svyazey_in(tochka_1, symbol):
    # функция создаёт (new_t) между загоревшейся внешней (.) (type = mozg or print) и posledniy_t
    global posledniy_t
    global posledniy_tp
    tochka_kortez = (tochka_1,)
    proverka_list = []
    poisk_type = tuple(cursor.execute("SELECT type FROM tochki WHERE ID = ?", tochka_kortez))
    for poisk_type1 in poisk_type:
        for poisk_type2 in poisk_type1:
            if poisk_type2 == 'mozg':
                # Проверить имеется ли уже связующая точка
                nayti_svyazi_s_signal_porog = tuple(cursor.execute(
                    "SELECT id_finish FROM svyazi WHERE id_start = ?", tochka_kortez))
                # print("Найдены следующие связи с nayti_tochki_signal_porog1: ", nayti_svyazi_s_signal_porog)
                for nayti_svyazi_s_signal_porog1 in nayti_svyazi_s_signal_porog:
                    for nayti_svyazi_s_signal_porog2 in nayti_svyazi_s_signal_porog1:
                        # print("posledniy_t = ", posledniy_t)
                        # print("nayti_svyazi_s_signal_porog2 (введённое in)= ", nayti_svyazi_s_signal_porog2)
                        proverka_nalichiya_svyazi = tuple(cursor.execute(
                            "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?", (
                                posledniy_t, nayti_svyazi_s_signal_porog2)))
                        # print("Нашли следующие ID у связей, где id_start = posledniy_t, id_finish = взятая из соседей", proverka_nalichiya_svyazi)
                        proverka_list += proverka_nalichiya_svyazi
                        # print("получился следующий список: ", proverka_list)
                        # print('лист проверки содержит следующее количество найденных ID связей: ', proverka_list)
                if not proverka_list:
                    # print("то есть proverka_list не пустой и всё равно прошли дальше?")
                    new_t = sozdat_new_tochky('time', 1, 'time', 'zazech_sosedey', 1, 0, 0,
                                              tochka_1, posledniy_t, symbol)
                    # print(f"Создана новая (т): {new_t}, где rod1 = {tochka_1} (точка in) и rod2 = {posledniy_t} (posledniy_t)")
                    sozdat_svyaz(tochka_1, new_t, 1)   # weight was 0.1
                    sozdat_svyaz(posledniy_t, new_t, 1)  # weight was 0.1
                    proverka_list = []
                    # v3.0.0 - posledniy_t становится новая связующая (.) м/у внешней горящей и старым posledniy_t
                    posledniy_t = new_t
                    # v3.1.0 - добавлено создание зеркальных сущностей у tp
                    poisk_svyazey_s_p = tuple(cursor.execute(
                            "SELECT id_finish FROM svyazi WHERE id_start = ?", tochka_kortez))
                    for poisk_svyazey_s_p1 in poisk_svyazey_s_p:
                        poisk_p = tuple(cursor.execute(
                            "SELECT ID FROM tochki WHERE ID = ? AND type = 'print'", poisk_svyazey_s_p1))
                        for poisk_p1 in poisk_p:
                            for poisk_p2 in poisk_p1:
                                new_tp = sozdat_new_tochky('time_p', 0, 'time', 'zazech_sosedey', 1, 0, 0, poisk_p2,
                                                           posledniy_tp, symbol)
                                sozdat_svyaz(new_tp, poisk_p2, 1)
                                sozdat_svyaz(posledniy_tp, new_tp, 1)
                                sozdat_svyaz(new_t, new_tp, 1)
                                posledniy_tp = new_tp
                else:
                    # если была найдена связующая (.) - значит к ней перейдёт posl_t
                    # print("proverka_list такой: ", proverka_list)
                    for proverka_list1 in proverka_list:
                        # print("proverka_list1 такой: ", proverka_list1)
                        naydennaya_tochka = tuple(cursor.execute(
                            "SELECT id_finish FROM svyazi WHERE ID = ?", proverka_list1))
                        for naydennaya_tochka1 in naydennaya_tochka:
                            for naydennaya_tochka2 in naydennaya_tochka1:
                                posledniy_t = naydennaya_tochka2
                                # print("posl_t стал такой: ", posledniy_t)
                                # v3.1.0 - в зеркальной сущности tp также должен произойти переход
                                poisk_svyzey_s_tp = tuple(cursor.execute(
                            "SELECT id_finish FROM svyazi WHERE id_start = ?", naydennaya_tochka1))
                                for poisk_svyzey_s_tp1 in poisk_svyzey_s_tp:
                                    poisk_tp = tuple(cursor.execute(
                                        "SELECT ID FROM tochki WHERE ID = ? AND name = 'time_p'", poisk_svyzey_s_tp1))
                                    for poisk_tp1 in poisk_tp:
                                        for poisk_tp2 in poisk_tp1:
                                            posledniy_tp = poisk_tp2


def proverka_nalichiya_svyazey_t_t_o():
    # функция создаёт (new_posl_t_o) между загоревшейся (posledniy_t) и (posledniy_t_0)
    global posledniy_t
    global posledniy_tp
    global posledniy_t_0
    print(f'Posledniy_t перед поиском связи time и time_0 теперь равен: {posledniy_t}')
    if posledniy_t != 0:
        # Поиск связи между post_t и posl_t0.
        # print(f"proverka_nalichiya_svyazey_t_t_o: posledniy_t_0 (rod1) = {posledniy_t_0} posledniy_t (rod2) = {posledniy_t}")
        # 06.12.23. Новая версия поиска точки, связывающей posl_t и posl_t0 (в 1 строку)
        poisk_svyazi_t_s_t0 = cursor.execute("SELECT ID FROM tochki WHERE rod1 = ? AND rod2 = ? AND name = 'time_0'",
                                             (posledniy_t_0, posledniy_t)).fetchall()
        # print(f"poisk_svyazi_t_s_t0 = {poisk_svyazi_t_s_t0}")
        name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", (posledniy_t,))
        for name2_2 in name2:
            novoye_name = name2_2[0]
            # print(f'name2_2[0] такой: {novoye_name}')
        if poisk_svyazi_t_s_t0 != []:
            # Такая точка существует - присвоить ей posl_t0
            for poisk_svyazi_t_s_t01 in poisk_svyazi_t_s_t0:
                posledniy_t_0 = poisk_svyazi_t_s_t01[0]
                # ydalit_svyaz(posledniy_t, posledniy_t_0)
                # sozdat_svyaz(posledniy_t_0, posledniy_t, 1)
                print(f"Posl_to после ввода in стал таким (такая точка имеется): {posledniy_t_0}")
        else:
            # 25.09.23 - Добавление 'name2' к t0, для возможности отсеивания по этому параметру
            new_t0 = sozdat_new_tochky('time_0', 0, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, posledniy_t,
                                       novoye_name+'/t')
            pereimenovat_name2_y_to(new_t0, posledniy_t)
            # print("Создана новая (t0): ", new_t0, " где rod1 = ", posledniy_t_0, " и rod2 = ", posledniy_t)
            sozdat_svyaz(posledniy_t_0, new_t0, 1)  # weight was 0.1
            sozdat_svyaz(posledniy_t, new_t0, 1)
            sozdat_svyaz(new_t0, posledniy_tp, 1)  # 21.06.23 - Добавил дублирующую связь от t0 к tp
            # v3.0.0 - posledniy_t становится новая связующая (.) м/у внешней горящей и старым posledniy_t
            posledniy_t_0 = new_t0
            print("После ввода in была создана новая t0 и posl_to теперь: ", posledniy_t_0)
        # 22.12.23 отсеивание, чтобы экран не попадал в кратковременную память

        # print(f'novoye_name содержит id_ekran_? -> {novoye_name}')
        if "id_ekran_" not in novoye_name:
            # 21.12.23 - Добавление (in) в память. Берётся именно последний (t)
            print(f'В in_pamyat: {in_pamyat} добавляется posledniy_t: {posledniy_t}')
            in_pamyat.append(posledniy_t)


def proverka_signal_porog():
    """ Находит и зажигает точки, у которых уровень сигнала больше, чем порог. Но если это точка, относящаяся к объектам
    на экране - она зажигается, только если определена (присутствует).
    """
    # print("Работа функции проверка сигнал порог")
    nayti_tochki_signal_porog = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal >= porog"))
    # 2.3.0 - ранее в nayti_tochki_signal_porog искались только (р), теперь сделал, чтобы находились все (...)
    # print("proverka_signal_porog. Нашли точки, у которых signal выше чем porog", nayti_tochki_signal_porog)
    for nayti_tochki_signal_porog1 in nayti_tochki_signal_porog:
        # print("proverka_signal_porog. Нашли точки: ", nayti_tochki_signal_porog1, " у которых signal выше чем porog")
        # print("zazech_sosedey. Проверка porog, какой у этой точки porog", nayti_tochki_signal_porog_proverka_signal)
        # 22.09.23 - ограничение на зажигание (t) и (tp), если не горят соответствующие (in) объекты:
        # поиск name2 - в нём хранится информация о хэше объекта
        nayti_name2 = tuple(cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", nayti_tochki_signal_porog1))
        if nayti_name2:
            for nayti_name2_1 in nayti_name2:
                # print(f"Нашли следующий name2: {nayti_name2_1} у точки: {nayti_tochki_signal_porog1}, "
                #       f"длина name2={len(nayti_name2_1)}")
                # если длина name2 = 16 - то это хэш
                if len(nayti_name2_1[0]) == 16:
                    # проверить горит ли такой же (in):
                    nayti_in = tuple(cursor.execute("SELECT ID FROM tochki WHERE name = ? AND work >= 1", nayti_name2[0]))
                    # print(f"Длина name2 = 16, найден соответствующий (in): {nayti_in}")
                    # если (in) горит - значит можно зажигать эту (t) или (tp):
                    if nayti_in:
                        # print("Этот (in) горит")
                        cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_tochki_signal_porog1)
                        cursor.execute("UPDATE tochki SET signal = 0.9 WHERE ID = (?)", nayti_tochki_signal_porog1)
                        cursor.execute("UPDATE tochki SET puls = 10 WHERE ID = (?) AND name = 'time_0'", nayti_tochki_signal_porog1)
                    else:
                        # если (in) не горит - погасить сигнал у этой (t)
                        # print(f"Этот (in): {nayti_tochki_signal_porog1} не горит. Обнуление сигнала")
                        cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = (?)", nayti_tochki_signal_porog1)
                else:
                    # если длина name2 не 16 - действуем по старому
                    # print("Длина name2 не равна 16")
                    cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_tochki_signal_porog1)
                    cursor.execute("UPDATE tochki SET signal = 0.9 WHERE ID = (?)", nayti_tochki_signal_porog1)
                    cursor.execute("UPDATE tochki SET puls = 10 WHERE ID = (?) AND name = 'time_0'", nayti_tochki_signal_porog1)



def pogasit_vse_tochki():
    # погасить все точки в конце главного цикла
    nayti_ID_s_work = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0"))    #!!! ранее был "AND work= 1"
    # print("погашены все точки: ", nayti_ID_s_work)
    for nayti_ID_s_work_1 in nayti_ID_s_work:
        cursor.execute("UPDATE tochki SET work = 0 WHERE ID = (?) AND name != '_most_'", nayti_ID_s_work_1)   # 19.12.23 добавлено "AND name != '_most_'"
        # cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = (?)", nayti_ID_s_work_1)   # 1.12.23 - убрал обнуление
    nayti_ID_s_work_1 = tuple(cursor.execute("SELECT ID FROM tochki WHERE work > 0 AND name != '_most_'"))    # 19.12.23 добавлено "AND name != '_most_'"
    # print("погашены все точки 2: ", nayti_ID_s_work_1)
    for nayti_ID_s_work2 in nayti_ID_s_work_1:
        cursor.execute("UPDATE tochki SET work = 0 WHERE ID = (?)", nayti_ID_s_work2)
        # cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = (?)", nayti_ID_s_work1)


def obnylit_signal_p():
    # обнуляет сигнал у (р), чтобы их не смогли зажечь (т), не являющиеся состоянием
    cursor.execute("UPDATE tochki SET signal = 0 WHERE type = 'print' AND signal > 0")


def zazech_sosedey(ID):
    # выполним действие зажечь соседей
    # Если горящие точки есть - то найдём связи у этих точек
    # print("Работа функции Зажечь соседей с ID = ", ID)
    nayti_id_svyaz = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ?", ID))
    if nayti_id_svyaz != ():  # если список связей не пустой - то идём дальше
        for nayti_id_svyaz1 in nayti_id_svyaz:
            # Найти вес связей
            ves_svyazi = tuple(cursor.execute("SELECT weight FROM svyazi WHERE ID = ?", nayti_id_svyaz1))
            for ves_svyazi1 in ves_svyazi:
                for ves_svyazi2 in ves_svyazi1:
                    id_tochki_soseda = tuple(cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?",
                                                            nayti_id_svyaz1))
                    # print("Сигнал", ves_svyazi2, "передаётся следующим соседям: ", id_tochki_soseda)
                    for id_tochki_soseda1 in id_tochki_soseda:
                        for id_tochki_soseda2 in id_tochki_soseda1:
                            cursor.execute("UPDATE tochki SET signal = signal + ? + 0.01 WHERE ID = ?",
                                           (ves_svyazi2, id_tochki_soseda2))   # Было до 16.03.23: cursor.execute("UPDATE tochki SET signal = signal + ? WHERE ID = ?", (ves_svyazi2, id_tochki_soseda2))
                            # 2.3.0 - если сигнал стал больше, чем порог - то прибавим к связи +вес
                            prov_tochki = tuple(cursor.execute("SELECT signal FROM tochki WHERE ID = ?",
                                                               id_tochki_soseda1))
                            # print('Сигнал у (',id_tochki_soseda2, '), которой передали сигнал такой: ', prov_tochki, ' должен быть больше 1')
                            # Если такая (.) нашлась - значит её сигнал выше, чем 1 (стандартный порог).
                            if prov_tochki != ():
                                cursor.execute("UPDATE svyazi SET weight = weight + 0.01 WHERE ID = ? AND weight < 1",
                                               nayti_id_svyaz1)
                        # если зажглись (+-) - то нужно сразу же провести работу с сигналом (т)
                        for id_tochki_soseda3 in id_tochki_soseda1:
                            if id_tochki_soseda3 == 2:
                                # если 2 - это (-) реакция - отнимем -1 от сигнала (т), чтобы в след. раз не загорелась
                                cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = 2")
                                cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 2")
    # гашение точки, которая отработала
    cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", ID)
    # cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", ID)   # убрал гашение сигнала
    # print("Зажечь соседей. Погашена отработанная точка: ", ID)
    proverka_signal_porog()



def gasheniye(ID):
    # функция обратная ф. "зажечь соседей" - она гасит соседей.
    nayti_id_svyaz = tuple(cursor.execute("SELECT id_finish FROM svyazi WHERE id_start = ?", ID))
    # print('список связей у гасящей точки: ', nayti_id_svyaz)
    if nayti_id_svyaz != ():  # если список связей не пустой - то идём дальше
        for nayti_id_svyaz1 in nayti_id_svyaz:
                # print('гасится следующая точка: ', nayti_id_svyaz1)
                cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", nayti_id_svyaz1)



def print1(ID):
    # print("print1. нашли следующие точки для ответа: ", ID)
    print("")
    otvet = tuple(cursor.execute("SELECT name FROM tochki WHERE ID = (?)", ID))
    print("")
    out_red(otvet)
    # print(otvet)
    cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", ID)



def out_red(text):
    global posledniy_otvet
    print("\033[31m {}".format(' '))
    print("\033[31m {}".format(text), '------------------')
    print("\033[0m {}".format("**********************************"))

    # Воспроизведение событий клавиатуры и мыши.
    # Данные в 1 списке, подрряд для всех событий:
    # Для клавиатуры 2 элемента: 'Key.down'/'Key.up', Клавиша (символ или название)
    # Для сочетаний клавиш, 'Key.hotkey', Название или id сочетания
    # Для мыши 4 элемента: 'Button.down'/'Button.up', 'left'/'right', 'x.y',  'image' (имя изображения элемента)
    # Пример: ['Button.down', 'left', 'elem_230307_144451.png', 'Button.up', 'left', 'Button.down',
    # 'left', 'elem_230228_163525.png', 'Button.up', 'left']
    # Для клика мыши сейчас только: 'click.image' (image - хэш элемента)
    i = 0
    while i < len(text):
        # print(f"Такой приходит текст: {text}")

        if '.' in text[i]:
            item = text[i].split('.')
            print(f'Преобразовали текст в item: {item}')
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

            else:
                i += 1
                continue
            try:
                play.play_one(event)  # Воспроизводим событие
            except:
                print('Выполнение скрипта остановлено')
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


def sozdat_svyaz(id_start, id_finish, weight):
    # проверим, есть ли уже такая связь
    proverka_svyazi = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?",
                                           (id_start, id_finish)))
    if id_start != id_finish:   # добавление проверки, чтоб не создалась закольцованная связь
        if proverka_svyazi == ():
            max_ID_svyazi = tuple(cursor.execute("SELECT MAX(ID) FROM svyazi"))
            for max_ID_svyazi1 in max_ID_svyazi:
                old_id_svyazi = max_ID_svyazi1[0]
                new_id_svyazi = old_id_svyazi + 1
            cursor.execute("INSERT INTO svyazi VALUES (?, ?, ?, ?)", (new_id_svyazi, id_start, id_finish, weight))
            # print(f'Создана связь м/у id_start = {id_start} и id_finish {id_finish}')
        else:
            for proverka_svyazi1 in proverka_svyazi:
                cursor.execute("UPDATE svyazi SET weight = weight + 0.1 WHERE ID = ?", proverka_svyazi1)



def ydalit_svyaz(id_start, id_finish):
    # проверить есть ли уже такая связь
    proverka_svyazi = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?",
                                           (id_start, id_finish)))
    if proverka_svyazi != ():
        for proverka_svyazi1 in proverka_svyazi:
            cursor.execute("DELETE FROM svyazi WHERE ID = ?", proverka_svyazi1)
            print(f'Удалена связь м/у id_start = {id_start} и id_finish {id_finish}')



def sozdat_new_tochky(name, work, type, func, porog, signal, puls, rod1, rod2, name2):
    max_ID = cursor.execute("SELECT MAX(ID) FROM tochki").fetchone()
    new_id = max_ID[0] + 1
    cursor.execute("INSERT INTO tochki VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id, name, work, type, func, porog, signal, puls, rod1, rod2, name2))
    return new_id



def vse_goryashie_tochki_f():
    # функция находит все горящие точки и выдаёт ID этих точек списком
    vse_goryashie_tochki_func = tuple(cursor.execute("SELECT ID FROM tochki WHERE work = 1"))
    return vse_goryashie_tochki_func



def functions():
    # c помощью этой функции найдём функцию точки и применим её
    goryashie_tochki_zazech_sosedey = tuple(cursor.execute(
        "SELECT ID FROM tochki WHERE func='zazech_sosedey' AND work >= 1"))
    # print("Следующие точки горят с ф. зажечь соседей: ", goryashie_tochki_zazech_sosedey)
    for goryashie_tochki_zazech_sosedey1 in goryashie_tochki_zazech_sosedey:
        zazech_sosedey(goryashie_tochki_zazech_sosedey1)
    rasprostranenie_potenciala()




def ymenshit_svyazi():
    # 2.3.0 - в конце цикла уменьшаем вес связи на 0,01, но если вес не равняется 1.
    cursor.execute("UPDATE svyazi SET weight = weight - 0.005 WHERE weight < 1 AND weight > 0.005")
    # 2.3.0 - если связь ушла в 0 - то она удаляется
    cursor.execute("DELETE FROM svyazi WHERE weight <= 0")



def concentrator_deystviy():
    """Если прошивка привела к тому, что возможного пути нет или все из возможных действий отрицательные - запускается
    эта функция. Она ищет все возможные (tp), у которых signal > 0 (т.е. даже затухающие).
    * Отсеиваются последние ответы, чтобы избежать зацикливания. Если это другой ответ - то записывается в лист.
    * Находится сигнал у всех действий в листе. Действия сортируются, исходя из наибольшего сигнала.
    * Перебираются действия и ищутся связи с (t0) или с (4), чтобы найти точку завершение сущности.
    * Ищется связь с последним t0 (текущим) и найденным. Если связи нет - добавить эту точку в лист действий.
    * Из листа действий удаляются дубли.
    * Передача действия в функцию, где производится поиск положительных и отрицательных реакций для их последующего
    влияния на выбор.
    """
    B = True
    global posledniy_t_0
    global posledniy_otvet
    global schetchik

    list_deystviy = []
    # 3.2.4 - соединение вместе и горящих и не горящих (tp) с последующим перебором вариантов
    list_tp = []
    list_signal_tp = []
    poisk_drygih_tp = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0 AND name = 'time_p'"))
    print("Запуск концентратора действий. Нашли следующие возможные (tp), у которых signal > 0 AND name = 'time_p': ", poisk_drygih_tp)
    if poisk_drygih_tp != ():
        for poisk_drygih_tp1 in poisk_drygih_tp:
            # 14.06.23 - добавление отсеивания совершённых ранее действий, чтобы не было зацикливания
            # print(f'Сравниваем текущую (tp) = {poisk_drygih_tp1} и последний ответ = {(posledniy_otvet,)}')
            if poisk_drygih_tp1 == (posledniy_otvet,):
                print('Последний ответ равен текущему ответу - проигнорировать ответ')
            else:
                # если ответ не равен последнему ответу - то сохраним это действие, как возможное
                # найдём signal у этих (tp)
                list_tp += poisk_drygih_tp1
                poisk_signal_tp = tuple(cursor.execute("SELECT signal FROM tochki WHERE ID = ?", poisk_drygih_tp1))
                # print("Сигнал у tp следующий: ", poisk_signal_tp)
                for poisk_signal_tp1 in poisk_signal_tp:
                    list_signal_tp += poisk_signal_tp1
        if list_tp != []:
            new_list_signal_tp, new_list_tp = zip(*sorted(zip(list_signal_tp, list_tp)))
            # print('Новый new_list_signal_tp: ', new_list_signal_tp, " Был таким: ", list_signal_tp)
            # print('Новый list_tp: ', new_list_tp, " Был таким: ", list_tp)
            # 3.2.4 - добавлен перебор вариантов действия (tp)
            schetchik_B = 0
            while B:
                list_t0 = []
                # print('Длина списка new_list_tp = ', len(new_list_tp), ' а если уменьшить на 1 : ', len(new_list_tp)-1)
                if len(new_list_tp)-1 >= schetchik_B:
                    # print("schetchik_B = ", schetchik_B)
                    poisk_tp = (new_list_tp[schetchik_B],)
                    # print("tp по которому будет проводиться поиск возможных действий: ", poisk_tp)
                    poisk_svyazi_s_t0 = tuple(cursor.execute("SELECT id_start FROM svyazi WHERE id_finish = ?", poisk_tp))
                    for poisk_svyazi_s_t01 in poisk_svyazi_s_t0:
                        # print("Найдены следующие связи tp c другими точками: ", poisk_svyazi_s_t01)
                        # из всех найденных связей оставим только связи с t0
                        poisk_t0 = tuple(cursor.execute("SELECT ID FROM tochki WHERE ID = ? AND name = 'time_0'",
                                                        poisk_svyazi_s_t01))
                        for poisk_t01 in poisk_t0:
                            list_t0 += poisk_t01
                    # print("Лист проверки на наличие связи с t0: ", list_t0)
                    if list_t0 == []:
                        # проверить имеется ли связь с 4
                        poisk_svyazi_s_4 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 4",
                                                                poisk_tp))
                        # print('Найдены следующие связи с (4): ', poisk_svyazi_s_4)
                        if poisk_svyazi_s_4 != ():
                            # print('Добавлено действие из-за наличия связи с (4)', poisk_tp)
                            list_deystviy += poisk_tp
                            # B = False # 3.2.5 - погасил
                        else:
                            # 3.2.5 - добавлено гашение сигнала, чтобы убрать "лишние" (tp)
                            # print('Погашена лишняя tp: ', poisk_tp)
                            # т.е. погашена tp, которая входит внутрь сущности
                            cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", poisk_tp)
                    else:
                        # Проверка - имеется ли связь с posl_t0 и найденным t0
                        for list_t01 in list_t0:

                            # print('Поиск связи между posledniy_t_0 = ', posledniy_t_0, 'и list_t01 = ', list_t01)
                            poisk_svyazi_s_posl_t0 = tuple(
                                cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?",
                                               (posledniy_t_0, list_t01)))
                            # print('poisk_svyazi_s_posl_t0 = ', poisk_svyazi_s_posl_t0)
                            # не ищется ID... разделяю на 2 фильтр
                            if poisk_svyazi_s_posl_t0 == ():
                                list_deystviy += poisk_tp
                                # print('List_deystviy 4 стал следующим: ', list_deystviy)
                else:
                    B = False
                schetchik_B += 1
    # Удаление дублей из листа действий:
    list_deystviy = list(set(list_deystviy))
    print('Лист действий в концентраторе после фильтрации: ', list_deystviy)
    if list_deystviy != []:
        vliyanie_na_deystvie = []
        id_dlya_ydaleniya = []
        for list_deystviy1 in list_deystviy:
            # поиск связей с текущим ID (tp) и (t0)
            # print("Лист действий, такой ID передаётся для поиска влияния: ", list_deystviy1)
            # поиск положительных и отрицательных реакций, их вычитание и запись в лист для дальнейшего выбора (tp)
            vliyanie = (poisk_pol_i_otric_reakciy(list_deystviy1))
            if vliyanie > 0:
                vliyanie_na_deystvie.append(vliyanie)
            else:
                id_dlya_ydaleniya.append(list_deystviy1)
                # print(f'Было добавлено к ID: {list_deystviy1}, следующее влияние: {poisk_pol_i_otric_reakciy(list_deystviy1)}')

        # print(f"Удаляются следующие действия: {id_dlya_ydaleniya}")
        for index in id_dlya_ydaleniya:
            list_deystviy.remove(index)
            print(f'Удалено действие: {index}')
        # выбор действия, исходя из влияния
        # print(f'Лист действий после поиска влияния: {list_deystviy}. Влияние равно: {vliyanie_na_deystvie}')
        if vliyanie_na_deystvie:
            choice = random.choices(list_deystviy, weights=vliyanie_na_deystvie, k=1)[0]
            print(f'Случайный ответ следующий: {choice}')
            sbor_deystviya(choice, 0)
            pogasit_vse_tochki()  # 13.09.23 - добавил гашение всех точек, чтобы совершить случайное действие и ждать на
            # него реакцию
    else:
        if in_pamyat != 0:
            print("\033[31m {}".format(' '))
            print("\033[31m {}".format('Не понятно, что дальше делать. Возможно отсутствуют известные объекты. '
                                       'Необходима помощь или повторная отправка команды'), '------------------')
            print("\033[0m {}".format("**********************************"))
            rec.key_down = 'Key.space'



def poisk_pol_i_otric_reakciy(ID):
    """Поиск связанных с текущим ID реакций и вычитание из положительных - отрицательных."""
    # выбрать id_finish, где id_start - это ID, а id_finish должен быть t0
    # print(f"Разбирается следующий ID: {ID} для поиска влияния")
    poisk_t0_start = cursor.execute(
        "SELECT svyazi.id_start FROM svyazi WHERE svyazi.id_finish = ?", (ID,)).fetchall()
    for poisk_t0_start1 in poisk_t0_start:
        poisk_t0 = cursor.execute("SELECT ID FROM tochki WHERE ID = ? AND name = 'time_0'", poisk_t0_start1)
    svyazi_s_1 = []
    svyazi_s_2 = []
    poisk_puls2 = 0
    poloz_minus_otric = 0
    for poisk_t01 in poisk_t0:
        # print(f'Для учёта влияния найдены следующие (to): {poisk_t01}, связанные с {ID}')
        # найти и просуммировать связи (t0) с (1)
        poisk_svyazi_s_1 = tuple(cursor.execute(
                            "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 1", poisk_t01))
        if poisk_svyazi_s_1:
            for poisk_svyazi_s_11 in poisk_svyazi_s_1:
                svyazi_s_1.append(poisk_svyazi_s_11[0])
        poisk_svyazi_s_2 = tuple(cursor.execute(
            "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 2", poisk_t01))
        if poisk_svyazi_s_2:
            for poisk_svyazi_s_21 in poisk_svyazi_s_2:
                svyazi_s_2.append(poisk_svyazi_s_21[0])
        poisk_puls = tuple(cursor.execute("SELECT puls FROM tochki WHERE ID = ?", poisk_t01))
        if poisk_puls:
            for poisk_puls1 in poisk_puls:
                for poisk_puls2 in poisk_puls1:
                    poloz_minus_otric = len(svyazi_s_1) - len(svyazi_s_2)/100 + poisk_puls2   # Влияние отрицательных связей уменьшено в 100 раз
    # print(f'Найдены положительные реакции: {svyazi_s_1}, найдены отрицательные реакции: {svyazi_s_2}, найден пульc: '
    #       f'{poisk_puls2}')
    # print(f'Получилось влияние на ответ: {poloz_minus_otric}')
    if poloz_minus_otric == 0:
        vliyanie = 1
    elif poloz_minus_otric >= -0.05:
        vliyanie = 0.05
    else:
        vliyanie = poloz_minus_otric
    return vliyanie



def create_dict(point_list, level, work_dict=dict(), max_level=5):
    """ Рекурсивная функция получающая все связи в виде словаря из БД """
    # print(f'Текущий level = {level}, max_level = {max_level}')
    if level == max_level:
        return work_dict
    else:
        # print(f'point_list = {point_list}')
        for point in point_list:
            # print(f'point = {point}')
            # Выбрать id_finish из связей, где id_finish = ID в табл. точки и id_start = point и name = time_0.
            points = cursor.execute(
                "SELECT svyazi.id_finish "
                "FROM svyazi JOIN tochki "
                "ON svyazi.id_finish = tochki.id "
                "WHERE svyazi.id_start = ? AND (tochki.name = 'time_0' OR tochki.name = 'time')", (point,)).fetchall()
            nodes = [row[0] for row in points]
            if nodes:
                work_dict[point] = nodes
                level += 1
                create_dict(work_dict[point], level, work_dict)
    return work_dict



def all_paths(tree, node):
    """ Рекурсивная функция получающая все пути из дерева """
    if node not in tree:
        return [[node]]
    paths = []
    for child_node in tree[node]:
        for path in all_paths(tree, child_node):
            paths.append([node] + path)
    return paths



def celevaya_proshivka():
    global in_pamyat



def proshivka_po_derevy(time_dlya_proshivki):
    """ Проверка возможности применения действий по пути из дерева.
        * Изначально, ищутся целевые tp. Т.е. те действия, которые нужно совершить, чтобы получить положительную реакцию.
        * Они находятся исходя из текущей in_pamyat (введённого задания) и с помощью деревьев, которые строятся из
        текущего (t). Нашли to (связанные с (+) из деревьев) - определили какие при этом совершались действия (tp) и
        нашли все (t0), которые связаны с этими действиями.
        * Дальше выполняется построение деревьев действий от текущего состояния и текущей (t).
        * Пути сортируются по возрастанию количества шагов и отсеиваются, если в них нет целевых (t0).
        * Вводится золотой путь, чтобы программа "не потерялась" при выполнении действий, а двигалась в нужном направлении.
        * Если золотого пути нет - то им становится первый из отсеянных новых путей. Если золотой путь есть - то
        проверяетсяего длина. Если новый путь короче - то он становится золотым.
        * Дальше происходит работа только с золотым путём, а не со всем массивом возможных путей.
        * Находится связь с 1 (+), 2 (-) и связь с изображениями, которых нет на экране.
        * Ограничено зажигание действий, если нет этого объекта на экране. !!!!
        * Если имеется связь с 1 (+) - то применить этот путь. Все остальные пути попадают в возможные действия.
        * Разбираются возможные действия. Если точка не в списке отрицательных и не в списке действий, объекты
        которых отсутствуют на экране - то применить это действие."""
    # todo Если вдруг нет элемента на экране - этот путь не может быть золотым.

    global posledniy_t_0
    global in_pamyat
    global in_pamyat_name
    global posledniy_t
    global posledniy_tp
    global zolotoy_pyt

    # 18.01.24 - дополнительная прошивка находит t0 с +, находит нужный tp, а затем находит все t0, которые с ним связаны
    # эти t0 и будут целевыми, по которым произойдёт отсеивание путей при поступательном движении к цели.

    print(f'Создаётся целевое дерево, где time: {in_pamyat[0]}')
    tree_celevoe = create_dict([in_pamyat[0]], 0)  # Получаем выборку связей в виде словаря (дерево)
    print(f"Возможный путь действий: ", all_paths(tree_celevoe, in_pamyat[0]))
    svyaz_s_1_celevoe = []
    celevoe_t0 = []
    for path_celevoe in all_paths(tree_celevoe, in_pamyat[0]):
        new_path_3_i_bolee_celevoe = path_celevoe[2:]
        # print(f'Рассматривается путь: {new_path_3_i_bolee_celevoe}')
        if new_path_3_i_bolee_celevoe:
            for tochka_celevoe in new_path_3_i_bolee_celevoe:
                # Поиск связи рассматриваемой точки и (+)
                proverka_nalichiya_svyazi_s_1_celevoe = tuple(cursor.execute(
                    "SELECT id_start FROM svyazi WHERE id_finish = 1 AND id_start = ?", (tochka_celevoe,)))
                for proverka_nalichiya_svyazi_s_1_celevoe1 in proverka_nalichiya_svyazi_s_1_celevoe:
                    if proverka_nalichiya_svyazi_s_1_celevoe1[0]:
                        poisk_tp_celevoe = cursor.execute("SELECT svyazi.id_finish "
                                                          "FROM svyazi JOIN tochki "
                                                          "ON svyazi.id_finish = tochki.id "
                                                          "WHERE svyazi.id_start = ? AND tochki.name = 'time_p'",
                                                          (tochka_celevoe,)).fetchall()
                        for poisk_tp_celevoe1 in poisk_tp_celevoe:
                            # print(f'Для поиска целевых tp была найдена t0: {proverka_nalichiya_svyazi_s_1_celevoe1}, '
                            #       f'у неё нашли связь с tp: {poisk_tp_celevoe1[0]}')
                            if poisk_tp_celevoe1[0] not in svyaz_s_1_celevoe:
                                svyaz_s_1_celevoe.append(poisk_tp_celevoe1[0])
    print(f'Найдены следующие (tp), которые являются целевыми: {svyaz_s_1_celevoe}')
    # теперь по этим (tp) ищутся все целевые t0
    for svyaz_s_1_celevoe1  in svyaz_s_1_celevoe:
        # Найти to (id_start) в связях, где id_finish - это tp, а name = time_0 из таблицы точки
        poisk_t0_celevoe = cursor.execute("SELECT svyazi.id_start "
                                          "FROM svyazi JOIN tochki "
                                          "ON svyazi.id_start = tochki.id "
                                          "WHERE svyazi.id_finish = ? AND tochki.name = 'time_0'",
                                          (svyaz_s_1_celevoe1,)).fetchall()
        # print(f'Найдены следующие целевые t0 от целевого tp: {poisk_t0_celevoe}')
        if poisk_t0_celevoe:
            for poisk_t0_celevoe1 in poisk_t0_celevoe:
                celevoe_t0.append(poisk_t0_celevoe1[0])
    print(f'Список целевых t0 по которым будет происходить отсеивание путей следующий: {celevoe_t0}')

    # Этап прошивки по текущему состоянию системы
    print(f'Создаётся дерево, где time: {time_dlya_proshivki}')
    tree = create_dict([time_dlya_proshivki], 0)  # Получаем выборку связей в виде словаря (дерево)
    vozmozhnie_deystviya = []
    otricatelnie_deystviya = []
    # print(f'Дерево действий такое: {tree}')
    print(f"Текущий t0 = {posledniy_t_0}. Возможный путь действий: ", all_paths(tree, time_dlya_proshivki))
    # print("Количество возможных путей действий: ", len(all_paths(tree, posledniy_t_0)))
    # Проверка имеется ли связь с 1 или 2 у точек на пути
    found = False
    pyti = all_paths(tree, time_dlya_proshivki)
    for path in sorted(pyti, key=len):
        svyaz_s_1 = []
        svyaz_s_2 = []
        svyaz_s_img = []
        # 18.01.24 - Отсеивание пути, если он не содержит целевые to.
        # 22.12.23 Удаляются 1 и 2 запись в пути. Везде вместо path вставил new_path_3_i_bolee
        new_path_3_i_bolee = path[2:]
        print(f'Был путь такой: {path}, а разбирается такой: {new_path_3_i_bolee}, фильтрация присутствует ли он в '
              f'целевых to: {celevoe_t0}')
        # Проверка - присутствуют ли элементы из проверяемого пути new_path_3_i_bolee в целевых to. Если да -
        # то работать с этим путём, а если нет - перейти на другой путь.
        proverka_prisutstviya = []
        if new_path_3_i_bolee:
            for element in new_path_3_i_bolee:
                if element in celevoe_t0:
                    proverka_prisutstviya.append(element)
            print(f'proverka_prisutstviya такая: {proverka_prisutstviya}')
            if proverka_prisutstviya:
                # 22.01.24 - дальнейшая работа ведётся только с золотым путём
                # 18.01.24 - Для проверки действия рассматривается только первый шаг из дерева, чтобы можно было
                # выполнить последовательность, а не перескакивать шаги
                # 18.01.24 - найти (tp) от этой точки и её записывать в списки
                poisk_tp = cursor.execute("SELECT svyazi.id_finish "
                                          "FROM svyazi JOIN tochki "
                                          "ON svyazi.id_finish = tochki.id "
                                          "WHERE svyazi.id_start = ? AND tochki.name = 'time_p'",
                                          (new_path_3_i_bolee[0],)).fetchall()
                for poisk_tp1 in poisk_tp:
                    print(f"Найдена tp: {poisk_tp1[0]}, связанная с t0 = {new_path_3_i_bolee[0]}. Дальше эта tp вписывается в списки")
                    proverka_nalichiya_svyazi_s_1 = tuple(cursor.execute(
                        "SELECT id_start FROM svyazi WHERE id_finish = 1 AND id_start = ?", (new_path_3_i_bolee[0],)))
                    # print(f'Нашли следующие связи c 1: {proverka_nalichiya_svyazi_s_1}')
                    for proverka_nalichiya_svyazi_s_1_1 in proverka_nalichiya_svyazi_s_1:
                        # print(f'Присоединение к svyaz_s_1: {proverka_nalichiya_svyazi_s_1_1[0]}')
                        if proverka_nalichiya_svyazi_s_1_1[0]:
                            if poisk_tp1[0] not in svyaz_s_1:
                                svyaz_s_1.append(poisk_tp1[0])

                    proverka_nalichiya_svyazi_s_2 = tuple(cursor.execute(
                        "SELECT id_start FROM svyazi WHERE id_finish = 2 AND id_start = ?", (new_path_3_i_bolee[0],)))
                    # print(f'Нашли следующие связи c 2: {proverka_nalichiya_svyazi_s_2}')
                    for proverka_nalichiya_svyazi_s_2_1 in proverka_nalichiya_svyazi_s_2:
                        # print(f'Присоединение к svyaz_s_2: {proverka_nalichiya_svyazi_s_2_1[0]}')
                        if proverka_nalichiya_svyazi_s_2_1[0]:
                            if poisk_tp1[0] not in svyaz_s_2:
                                svyaz_s_2.append(poisk_tp1[0])
                                # Погасить эту точку, чтобы не появилась в функции концентратор действий
                                cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", poisk_tp1)
                                cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", poisk_tp1)
                                # print(f'Погашена точка: {poisk_tp1}')
                                # points1 = cursor.execute("SELECT * FROM tochki WHERE ID = ?", poisk_tp1).fetchall()
                                # print(f"Проверка гашения точки: {points1}")
                            # если была найдена отрицательная реакция и эта точка является первой в укороченном пути
                            if proverka_nalichiya_svyazi_s_2_1[0] == new_path_3_i_bolee[0]:
                                # print(f'Добавилось отрицательное действие- т.к. оно второе в пути: {proverka_nalichiya_svyazi_s_2_1}')
                                    if poisk_tp1[0] not in otricatelnie_deystviya:
                                        otricatelnie_deystviya.append(poisk_tp1[0])

                    # 22.09.23 - ограничение на зажигание (t) и (tp), если не горят соответствующие (in) объекты:
                    # поиск name2 - в нём хранится информация о хэше объекта
                    nayti_name2 = tuple(cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", (new_path_3_i_bolee[0],)))
                    if nayti_name2:
                        for nayti_name2_1 in nayti_name2:
                            # print(f"Нашли следующий name2: {nayti_name2_1[0]} у точки: {new_path_3_i_bolee[0]}, "
                            #       f"длина name2={len(nayti_name2_1[0])}")
                            name2_1 = nayti_name2_1[0]
                            # если длина name2 = 18 - то это хэш
                            if len(nayti_name2_1[0]) in [18, 19]:
                                # Необходимо удалить 2 последних знака из name2, чтобы получился name
                                if len(nayti_name2_1[0]) == 18:
                                    new_name = name2_1[:-2]
                                    # print(f'name2 был такой: {name2_1}, а стал такой: {new_name}')
                                elif len(nayti_name2_1[0]) == 19:
                                    new_name = name2_1[:-3]
                                    # print(f'name2 был такой: {name2_1}, а стал такой: {new_name}')
                                # проверить горит ли такой же (in):
                                nayti_in = tuple(
                                    cursor.execute("SELECT ID FROM tochki WHERE name = ? AND work < 1 "
                                                   "AND type = 'mozg'", (new_name,)))
                                # print(f"Длина name2 у to ({new_path_3_i_bolee[0]}) = 18, найден соответствующий (in), который не горит: {nayti_in}")
                                if nayti_in:
                                    # print(f'Добавлена точка в svyaz_s_img, теперь список такой: {svyaz_s_img}')
                                    # print("Этот (in) не горит - пропуск точки, переход к следующей")
                                    if new_path_3_i_bolee[0] not in svyaz_s_img:
                                        svyaz_s_img.append(poisk_tp1[0])
                    if poisk_tp1[0] not in (svyaz_s_1 or svyaz_s_2 or svyaz_s_img):
                        print(f'Точка действия: {poisk_tp1[0]}, отсутствует в списках: svyaz_s_1 - {svyaz_s_1}, svyaz_s_2 - {svyaz_s_2}, '
                              f'svyaz_s_img - {svyaz_s_img} и добавлена в vozmozhnie_deystviya - {vozmozhnie_deystviya}')
                        if poisk_tp1[0] not in vozmozhnie_deystviya:
                            vozmozhnie_deystviya.append(poisk_tp1[0])
                print(f'Собраны следующие списки: svyaz_s_1 - {svyaz_s_1}, svyaz_s_2 - {svyaz_s_2}, svyaz_s_img - '
                      f'{svyaz_s_img}, vozmozhnie_deystviya - {vozmozhnie_deystviya}, otricatelnie_deystviya - '
                      f'{otricatelnie_deystviya}')

                # 22.01.24 - Внедрён золотой путь.
                print(f'Длина золотого пути: {len(zolotoy_pyt)}, длина нового пути: {len(new_path_3_i_bolee)}')
                if len(zolotoy_pyt) > len(
                        new_path_3_i_bolee):  # Если путь не является золотым - то он и не будет рассмотрен
                    print(f'Путь: {new_path_3_i_bolee} стал золотым: {zolotoy_pyt} т.к. новый короче')
                    zolotoy_pyt = new_path_3_i_bolee
                else:
                    if len(zolotoy_pyt) == 0:
                        print(f'Путь: {new_path_3_i_bolee} теперь золотой путь (был пустым)')
                        zolotoy_pyt = new_path_3_i_bolee

                if svyaz_s_1 and not svyaz_s_2 and not svyaz_s_img:
                    # Если имеется связь с (+) - то применить этот путь
                    poisk_tp_v_pervoy_tochke_pyti = tuple(cursor.execute("SELECT svyazi.id_finish "
                    "FROM svyazi JOIN tochki "
                    "ON svyazi.id_finish = tochki.id "
                    "WHERE svyazi.id_start = ? AND tochki.name = 'time_p'", (new_path_3_i_bolee[0],)))
                    print(f'Применить действие, если t0 - start: {poisk_tp_v_pervoy_tochke_pyti}')
                    if poisk_tp_v_pervoy_tochke_pyti:
                        for poisk_tp_v_pervoy_tochke_pyti1 in poisk_tp_v_pervoy_tochke_pyti:
                            print(f"Совершается действие {poisk_tp_v_pervoy_tochke_pyti1}")
                            sbor_deystviya(poisk_tp_v_pervoy_tochke_pyti1[0], svyaz_s_1_celevoe)
                            print(f'Совершено первое действие {zolotoy_pyt} - удалить из списка')
                            zolotoy_pyt.pop(0)
                            found = True   # выход из внешнего цикла
                            break
                    if found:
                        break  # выход из внешнего цикла
                elif svyaz_s_img:
                    # Если объекта нет на экране - то золотой путь обнуляется
                    zolotoy_pyt = []
                    print(f'Объекта нет на экране - золотой путь обнулился')
                    break
        if found:
            break  # выход из внешнего цикла

    # print(f"found = {found}")
    if not found:
        # Если нет действия только с положительной реакцией - то применить первое действие из возможных
        found1 = False
        print(f'Возможные действия: {vozmozhnie_deystviya}')
        # print(f'Количество возможных действий: {len(vozmozhnie_deystviya)}')
        # print(f'svyaz_s_img такой: {svyaz_s_img}')
        if vozmozhnie_deystviya:
            for vozmozhnie_deystviya1 in vozmozhnie_deystviya:
                # Проверить является ли эта точка отрицательной.
                # print(f'Проверка имеется ли возможное действие {vozmozhnie_deystviya1} в списках: отрицательные действия: '
                #       f'{otricatelnie_deystviya}, связь с 5: {svyaz_s_5}, связь с img: {svyaz_s_img}')
                if not vozmozhnie_deystviya1 in otricatelnie_deystviya:
                    # if not vozmozhnie_deystviya1 in svyaz_s_5:
                        # print(f'Применить возможное действие: {vozmozhnie_deystviya1}')
                                print(f'Совершается первое действие из списка возможных: {vozmozhnie_deystviya1}')
                                sbor_deystviya(vozmozhnie_deystviya1, svyaz_s_1_celevoe)
                                print(f'Совершено первое действие {zolotoy_pyt} - удалить из списка')
                                zolotoy_pyt.pop(0)
                                found1 = True
                                break
                if found1:
                    break
        if not found1:
            # 11.01.24 - Если нет действий - то разбить сущность на составляющие (она уже разбита в in_pamyat_name).
            # Этот список вставить в начало in_pamyat вместо первого рассматриваемого элемента
            if in_pamyat_name:
                # удаляется первый элемент из in_pamyat и на место него вставляются элементы из in_pamyat_name
                print(f'удаляется первый элемент из in_pamyat: {in_pamyat} и на место него вставляются элементы из '
                      f'in_pamyat_name: {in_pamyat_name}')
                in_pamyat.pop(0)
                naydennie_id_name = []
                for in_pamyat_name1 in in_pamyat_name:
                    # print(f'Для добавления в in_pamyat ищется следующий ID у name: {in_pamyat_name1}')
                    for in_pamyat_name2 in in_pamyat_name1:
                        poisk_bykvi_iz_vvedeno_v2(in_pamyat_name2)
                    # print(f'В naydennie_id_name добавлен следующий posledniy_t: {posledniy_t}')
                    naydennie_id_name.append(posledniy_t)
                    posledniy_tp = 0
                    posledniy_t = 0
                # print(f'naydennie_id_name перед совмещением с in_pamyat: {naydennie_id_name}')
                in_pamyat = naydennie_id_name + in_pamyat
                print(f'Получается следующая in_pamyat: {in_pamyat}')
                in_pamyat_name = []
                # создать новую (t0), где связь будет с первым элементом in_pamyat
                new_t0 = sozdat_new_tochky('time_0', 1, 'time', 'zazech_sosedey', 1, 0,
                                           0, posledniy_t_0, in_pamyat[0], '')
                sozdat_svyaz(posledniy_t_0, new_t0, 1)
                sozdat_svyaz(in_pamyat[0], new_t0, 1)
                posledniy_t_0 = new_t0
                posledniy_tp = 0
                posledniy_t = 0
                # print(f'После ввода первого элемента in posl_t0 должен перейти на: {posledniy_t_0}')
            else:
                # Для выполнения циклов последовательных действий после того, как программа выполнила действий в первом
                # задании - она должна перейти к следующему заданию, которое теперь находится в первом элементе in_pamyat -
                # т.к. предыдущий первый элемент был удалён. Но если не было совершено действий и состояние не изменилось - значит
                # нет возможных путей действий для этого задания - нужно запустить концентратор действий, чтобы сдвинуть
                # выполнение задание на один шаг, используя доступные действия.
                # todo Добавить связь между целевым t0 и t? Чтобы была возможность использовать потенциал зажигания для выбора наиболее подходящих действий.

                # Проверить - текущее состояние - это тоже самое состояние, связанное с in_pamyat[0]. Найти связь м/у
                # первым in_pamyat и t0. Если t0 = текущему posledniy_t0 - то состояние не переводится, а включается
                # концентратор действий.
                proverka_sostoyaniya = cursor.execute("SELECT svyazi.id_finish FROM svyazi JOIN tochki ON svyazi.id_finish = tochki.ID"
                                " WHERE svyazi.id_start = ? AND tochki.name = 'time_0' ", (in_pamyat[0],)).fetchone()

                for proverka_sostoyaniya1 in proverka_sostoyaniya:
                    print(f'Нашлись следующие связи ')
                    print(f'Текущее состояние (posledniy_t0) = {posledniy_t_0}, а проверка состояние для перевода в '
                          f'первый элемент in_pamyat = {proverka_sostoyaniya1[0]}')
                    if proverka_sostoyaniya1[0] != posledniy_t_0:
                        print(f"Нет возможных путей действий... Состояние принудительно переводится в 1 элемент in_pamyat: {in_pamyat}")
                        new_t0 = sozdat_new_tochky('time_0', 1, 'time', 'zazech_sosedey', 1, 0,
                                                   0, posledniy_t_0, in_pamyat[0], '')
                        sozdat_svyaz(posledniy_t_0, new_t0, 1)
                        sozdat_svyaz(in_pamyat[0], new_t0, 1)
                        posledniy_t_0 = new_t0
                        posledniy_tp = 0
                        posledniy_t = 0
                    else:
                        print("Нет больше возможных путей и стёрто последнее in_pamyat - включается концентратор действий")
                        concentrator_deystviy()



def sbor_deystviya(tp, celevoe_tp):
    # собирает в обратном порядке сущность от последнего tp и приводит в действие ответ
    # print("Разбирается следующий tp для ответа: ", tp)
    global posledniy_t_0
    global posledniy_otvet
    global in_pamyat
    B = True
    tp_kortez = (tp, )

    # 19.01.24 - Если выполняемое действие является целевым - то удалить первый элемент из in_pamyat
    print(f'В сборе действий проверяется является ли выполняемое tp: {tp} целевым: {celevoe_tp}, если да - то удалится'
          f' первый элемент из in_pamyat: {in_pamyat}')
    if tp in celevoe_tp:
        in_pamyat.pop(0)

    # 22.06.23 - гашение ответов, для блокировки повторов.
    cursor.execute("UPDATE tochki SET work = 0 AND signal = 0 WHERE ID = ?", (tp,))

    #14.06.23 - ввод запоминания последнего ответа, для блокирования повторов
    posledniy_otvet = tp
    # print(f'Последний ответ стал равен: {posledniy_otvet}')

    # 3.2.2 - добавляется поиск уже имеющегося t0 и проверяется - имеется ли связь с posl_t0
    poisk_svyazi_tp_s_t0 = tuple(cursor.execute("SELECT ID FROM tochki WHERE rod1 = ? AND name = 'time_0' AND rod2 = ?",
                                                (posledniy_t_0, tp)))
    # 21.12.23 - добавляется поиск связи от posl_t0 к time
    poisk_time = cursor.execute("SELECT svyazi.id_start FROM svyazi JOIN tochki ON svyazi.id_start = tochki.ID"
                                " WHERE svyazi.id_finish = ? AND tochki.name = 'time' ", (tp,))

    # 22.06.23 - если передаётся t0 - то он и становится posl_t0
    if poisk_svyazi_tp_s_t0 == ():
        # 25.09.23 - Добавление 'name2' к t0, для возможности отсеивания по этому параметру
        name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", (tp,))
        for name2_1 in name2:
            # print(f'Найден name2: {name2_1} у точки: {tp}')
            # создать t0 и к нему привязать tp
            new_tochka_t0 = sozdat_new_tochky('time_0', 0, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, tp,
                                              name2_1[0]+'/tp')
            # print(f'создана new_tochka_t0 такая: {new_tochka_t0}, а была posl_t0 = {posledniy_t_0}')
            # sozdat_svyaz(new_tochka_t0, tp, 1)  # 3.2.2 - убрал обратную связь
            sozdat_svyaz(posledniy_t_0, new_tochka_t0, 1)
            sozdat_svyaz(new_tochka_t0, tp, 1)
            posledniy_t_0 = new_tochka_t0
            print("Posl_to (5) из-за сбора действий и создания новой t0 = ", posledniy_t_0)
            # 21.12.23 - Добавление связи от posl_t0 к time
            if poisk_time:
                for poisk_time1 in poisk_time:
                    sozdat_svyaz(poisk_time1[0], posledniy_t_0, 1)
    else:
        for poisk_svyazi_tp_s_t01 in poisk_svyazi_tp_s_t0:
            for poisk_svyazi_tp_s_t02 in poisk_svyazi_tp_s_t01:
                posledniy_t_0 = poisk_svyazi_tp_s_t02
                print("Posl_to теперь в сборе действий, когда нашлось нужное t0 стал = ", posledniy_t_0)
                # cursor.execute("UPDATE tochki SET work = 1 WHERE ID = ?", (posledniy_t_0,))
                # if poisk_time:
                #     for poisk_time1 in poisk_time:
                #         # 21.12.23 - разворачивается связь
                #         ydalit_svyaz(poisk_time1[0], posledniy_t_0)
                #         sozdat_svyaz(posledniy_t_0, poisk_time1[0], 1)
    list_deystviy = []
    list_deystviy += tp_kortez
    list_tp = []
    poisk_svyazi_s_tp = tuple(cursor.execute("SELECT id_start FROM svyazi WHERE id_finish = ?", tp_kortez))
    # print('poisk_svyazi_s_tp:  ', poisk_svyazi_s_tp)
    if poisk_svyazi_s_tp != ():
        while B:
            if poisk_svyazi_s_tp != ():
                for poisk_svyazi_s_tp1 in poisk_svyazi_s_tp:
                    poisk_type_tp = tuple(cursor.execute("SELECT ID FROM tochki WHERE ID = ? AND name = 'time_p'",
                                                         poisk_svyazi_s_tp1))
                    # сразу записать в лист не tp, а (р)?
                    list_tp += poisk_type_tp
                if list_tp != []:
                    for poisk_type_tp1 in list_tp:
                        # print("poisk_type_tp = ", poisk_type_tp1)
                        # найдена предыдующая (.) tp - запишем в лист
                        list_deystviy += poisk_type_tp1
                        # запускается новый поиск следующей связи с предыдущей (tp)
                        poisk_svyazi_s_tp = tuple(
                            cursor.execute("SELECT id_start FROM svyazi WHERE id_finish = ?", poisk_type_tp1))
                        # print('poisk_svyazi_s_tp: ', poisk_svyazi_s_tp)
                    list_tp = []
                else:
                    B = False
            else:
                B = False
    # print("Собран следующий лист действий, который нужно перевернуть: ", list_deystviy)
    list_deystviy.reverse()

    list_p = []
    for list_deystviy1 in list_deystviy:
        otvet_kortez = (list_deystviy1,)
        # ищутся сами (р) для формирования ответа
        poisk_svyazi_s_p = tuple(cursor.execute("SELECT id_finish FROM svyazi WHERE id_start = ?", otvet_kortez))
        for poisk_svyazi_s_p1 in poisk_svyazi_s_p:
            poisk_p = cursor.execute("SELECT name FROM tochki WHERE ID = ? AND type = 'print'",
                                                         poisk_svyazi_s_p1).fetchone()
            if poisk_p:
                list_p.append(poisk_p[0])
    # print(f'posledniy_t0 перед ответом: {posledniy_t_0}')
    if list_p != []:
        print("Ответ программы: ")
        out_red(list_p)
        print("")


def sozdat_svyaz_s_4():
    # функция берёт posl_tp и соединяет с (4), если такой связи нет - тем самым создавая сущность
    global posledniy_tp
    posledniy_tp_kortez = (posledniy_tp, )
    poisk_svyazi_s_4 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 4",
                                   posledniy_tp_kortez))
    if poisk_svyazi_s_4 == ():
        # если такой связи нет - создать
        sozdat_svyaz(posledniy_tp, 4, 1)


def sozdat_svyaz_s_4_ot_luboy_tochki(tochka):
    # в функцию передаётся ID точки и соединяет с (4), если такой связи нет - тем самым создавая сущность
    poisk_svyazi_s_4 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 4", (tochka,)))
    if poisk_svyazi_s_4 == ():
        # если такой связи нет - создать
        sozdat_svyaz(tochka, 4, 1)


def ymenshenie_signal():
    # функция находит все (.), где сигнал более 0 и уменьшает на 0,1 или на 0,01
    ymenshenie_signal_ = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal >= 0.01"))
    cursor.execute("UPDATE tochki SET signal = signal - 0.1 WHERE signal >= 0.1 AND signal < 1")
    cursor.execute("UPDATE tochki SET signal = signal - 0.01 WHERE signal >= 0 AND signal < 0.1")
    # print("Уменьшен сигнал у следующих точек: ", ymenshenie_signal_)



def perenos_sostoyaniya():
    # Функция определяет какой сейчас экран, отличается ли от старого. Если отличается - перенос posl_t0 в этот экран
    global old_ekran
    global posledniy_t_0
    global posledniy_t
    global posledniy_tp
    id_ekran = screen.screenshot_hash
    new_name_id_ekran = "id_ekran_" + str(id_ekran)
    print(f'Новый нейм экрана: {new_name_id_ekran}')
    poisk_bykvi_iz_vvedeno_v2(new_name_id_ekran)
    print(f"Сейчас такой экран ID: {posledniy_t}, старый экран такой: {old_ekran}")
    if old_ekran != posledniy_t:
        proverka_nalichiya_svyazey_t_t_o()
        old_ekran = posledniy_t
    else:
        print('!!!!!!!!!!!!!ВНИМАНИЕ!!!!!!ЭКРАН НЕ ИЗМЕНИЛСЯ!!!!!!!!!!!')
    posledniy_t = 0
    posledniy_tp = 0



def rasprostranenie_potenciala():
    """Функция, которая отмечает обратных соседей (расположенных на начале стрелки, а не на конце) у загоревшихся
    точек. Чтобы оказать влияние на выбор следующего действия (зажигания точки действия)."""
    poisk_puls = tuple(cursor.execute("SELECT ID FROM tochki WHERE puls > 0"))
    if poisk_puls:
        for poisk_puls1 in poisk_puls:
            # сложный поиск, где находится ID start, если задан id_finish, при этом id_start должен быть с name = time_0
            poisk_obratnogo_soseda_id_start = tuple(cursor.execute("SELECT svyazi.id_start "
                                                                 "FROM svyazi JOIN tochki "
                                                                 "ON svyazi.id_finish = tochki.id "
                                                                 "WHERE svyazi.id_finish = ?",
                                                                 (poisk_puls1[0],)))
            # отсеивание poisk_obratnogo_soseda_id_start должен быть с name = time_0
            for poisk_obratnogo_soseda_id_start1 in poisk_obratnogo_soseda_id_start:
                poisk_obratnogo_soseda = tuple(cursor.execute(
                    "SELECT ID FROM tochki WHERE ID = ? AND name = 'time_0'", poisk_obratnogo_soseda_id_start1))
                for poisk_obratnogo_soseda1 in poisk_obratnogo_soseda:
                    # print(f"Нашли обратного соседа: {poisk_obratnogo_soseda1[0]}, у точки: {poisk_puls1} и распространился "
                    #       f"потенциал")
                    puls_etogo_ID = tuple(cursor.execute("SELECT puls FROM tochki WHERE ID = ?", poisk_puls1))
                    for puls_etogo_ID1 in puls_etogo_ID:
                        # print(f"Пульс текущего ID равен: {puls_etogo_ID1[0]}")
                        new_puls = puls_etogo_ID1[0]-1
                    # print(f"Обновляется puls у обратного соседа: {poisk_obratnogo_soseda1[0]}, new_puls = {new_puls}, "
                    #       f"но новый должен быть больше старого")
                    # проверка старого пульса
                    # puls_stariy = tuple(cursor.execute("SELECT puls FROM tochki WHERE ID = ?", poisk_obratnogo_soseda1))
                    # обновление пульса
                    cursor.execute("UPDATE tochki SET puls = ? WHERE ID = ?", (new_puls,
                                                                               poisk_obratnogo_soseda1[0]))
                    # увеличение сигнала, чтобы была возможность найти точку в функции концентратор действий
                    # print(f"poisk_obratnogo_soseda1[0]: {poisk_obratnogo_soseda1[0]}")
                    cursor.execute("UPDATE tochki SET signal = 0.1 WHERE ID = ? AND signal < 0.1",
                                       (poisk_obratnogo_soseda1[0], ))
                    # Проверка увеличение пульса
                    # puls_proverka = tuple(cursor.execute("SELECT puls FROM tochki WHERE ID = ?", poisk_obratnogo_soseda1))
                    # for puls_proverka1 in puls_proverka:
                        # print(f"Старый пульс = {puls_stariy[0]}, передаваемый: {new_puls}, теперь он равен: {puls_proverka1}")
            # обнуляется родительский puls
            cursor.execute("UPDATE tochki SET puls = 0 WHERE ID = ?", poisk_puls1)


def pereimenovat_name2_y_to(ID, rod2):
    """Функция переименовывает name2 у t0 (передаваемое ID) если имеется связанная t/tp, которая в свою очередь связана
    с key.tap
    """
    # найти rod2 (связанную точку t или tp) у текущей t0
    nayti_rod2_y_t = cursor.execute("SELECT rod2 FROM tochki WHERE ID = ?", (rod2, )).fetchall()
    # print(f'nayti_rod2_y_t: {nayti_rod2_y_t}')
    for nayti_rod2_y_t1 in nayti_rod2_y_t:
        # найти name2 у этой ID = rod2
        nayti_name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", nayti_rod2_y_t1).fetchall()
        # print(f'Найден name2 = {nayti_name2} у точки {nayti_rod2_y_t1}, которая связана с t/tp: {rod2} текущего t0: '
        #       f'{ID}')
        if nayti_name2:
            for nayti_name21 in nayti_name2:
                # print(f'Key.tap = {nayti_name21[0]} ?')
                if nayti_name21[0] == 'Key.tap':
                    # если это нажатие на кнопку - то вписать в name2 t0 дополнительно /key
                    cursor.execute("UPDATE 'tochki' SET name2 = name2 || '/Key' WHERE ID = ?", (ID, ))
                    print(f'Должно обновиться name2 у точки: {ID}')





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
    posledniy_t = 0
    posledniy_t_0 = 3
    posledniy_tp = 0
    posledniy_otvet = 0
    t0_10 = 0   # для проверки на изменение to за 10 циклов

    source = None  # Получает значение источника ввода None - клавиатура, 'rec' -  запись клавиатуры и мыши
    last_update_screen = 0  # Время последнего обновления экрана
    schetchik = 0
    most_new = 0
    time.sleep(0.1)

    in_pamyat = []   # 20.12.23 - Список для хранения входящих ID (in)
    in_pamyat_name = []   #12.01.24 - Список для хранения входящих в виде name, а не ID
    zolotoy_pyt = []   # 19.01.24 - Путь, являющийся самым коротким для достижения положительного результата

    perenos_sostoyaniya()   # 30.11.23 - убрал posledniy_t_0=3 и поставил сразу перенос состояния в экран


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
        if scrsh is not None:
            # -------------------------------
            # Сохранение изображений в отчете
            report.set_folder('update_points')  # Инициализация папки для сохранения изображений
            scr = report.circle_an_object(scrsh, screen.hashes_elements.values())  # Обводим элементы
            report.save(scr)  # Сохранение скриншота и элемента
            # -------------------------------

        # Если экран обновился (определяется по времени), то обновляем точки
        # last_update_screen = screen.last_update
        # Деактивация точек относящихся к элементам экрана
        cursor.execute("UPDATE 'tochki' SET work = 0 WHERE type = 'mozg' AND length(name) = 16")
        # Активация точек относящихся к элементам экрана, которые есть на текущем экране
        list_goryashih_in = []
        for h in screen.get_all_hashes():
            cursor.execute("UPDATE 'tochki' SET work = 1 WHERE type = 'mozg' AND name = ?", (h,))
            goryashie_in = cursor.execute("SELECT ID FROM tochki WHERE work = 1 AND type = 'mozg' "
                                          "AND name = ?", (h,)).fetchall()
            if goryashie_in:
                list_goryashih_in.append(goryashie_in)
        print(f'Имеются следующие объекты на экране записанные в БД: {list_goryashih_in}')

        # -------------------------------------------------------
        # print(f'Найдены элементы на экране (все возможные): {screen.get_all_hashes()}')
        # Прочитать из БД и распечатать точки, которые могли быть изменены
        # points = cursor.execute("SELECT ID FROM tochki WHERE work = 1").fetchall()
        # print(f"Горят следующие точки: {points}")

        schetchik += 1
        print('************************************************************************')
        print("schetchik = ", schetchik, "     Экран", screen.screenshot_hash)

        proverka_signal_porog()   # проверка и зажигание точек, если signal >= porog

        # print("Сейчас ", source)
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
                    if event['event'] == 'click':
                        vvedeno_luboe.append('click.' + event['image'])
                    #     vvedeno_luboe.append('position.' + str(event['x']) + '.' + str(event['y']))
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

        # print('ввели: ', vvedeno_luboe)
        if vvedeno_luboe == ('0'):
            tree = ()
            A = False
            in_pamyat = []
            continue

        elif vvedeno_luboe == ('1'):
            """Создаётся связь м/у положительной реакцией и текущим состоянием. При вводе - стирается первый введённый 
             элемент задания (памяти) и состояние переводится на текущий экран."""
            # Нужно проверить имеется ли уже связь м/у t0 и tp
            # print("Состояние перед (+) реакцией было такое: ", posledniy_t_0, ". С ней и создаётся связь")
            sozdat_svyaz(posledniy_t_0, 1, 1)

            # source = None
            vvedeno_luboe = ''

            schetchik = 0  # 12.09.23 Добавил переход к началу цикла, если была применена реакция
            posledniy_tp = 0
            posledniy_t = 0
            posledniy_t_0 = 0
            posledniy_t = old_ekran
            proverka_nalichiya_svyazey_t_t_o()
            posledniy_t = 0
            print(f'Posl_t0 из-за (+) стал = {posledniy_t_0}. Состояние скинуто до старого экрана. ')
            print(f'in_pamyat перед удалением первого элемента: {in_pamyat}')
            if in_pamyat:
                in_pamyat.pop(0)
                print(f'Удалён первый элемент из in_pamyat, теперь список такой: {in_pamyat}')
            if in_pamyat_name:
                in_pamyat_name.pop(0)
                print(f'Удалён первый элемент из in_pamyat_name, теперь список такой: {in_pamyat_name}')
        elif vvedeno_luboe == ('2'):
            # нужно проверить имеется ли уже связь м/у t0 и tp
            print("Состояние перед (-) реакцией было такое: ", posledniy_t_0,". С ней и создаётся связь")
            sozdat_svyaz(posledniy_t_0, 2, 1)
            source = None
            vvedeno_luboe = ''
            # schetchik = 0   # 12.09.23 Добавил переход к началу цикла, если была применена реакция
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
                    poisk_predidushego_t0 = cursor.execute("SELECT rod1 FROM tochki WHERE ID = ?",
                                                           (posl_t0_dlya_cicla, )).fetchall()
                    # проверить какой длины name2 - если 16 знаков - то это клик и искать следующую t0
                    for poisk_predidushego_t01 in poisk_predidushego_t0:
                        proverka_name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ? "
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
            else:
                pogasit_vse_tochki()
                posledniy_t_0 = 0
                posledniy_t = old_ekran
                proverka_nalichiya_svyazey_t_t_o()
                posledniy_t = 0
                print(f'Posl_t0 из-за (-) стал = {posledniy_t_0}, при этом моста нет')

        elif vvedeno_luboe == ('3'):
            # Включение записи
            cursor.commit()  # Сохраняем изменения в БД
            sleep(0.5)
            rec.start()
            # source = None  # Запись сохранится в месте ввода
            continue

        elif vvedeno_luboe == ('4'):
            # Показать запись
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

        elif vvedeno_luboe == ('5'):
            # Сохранение записи
            source = 'rec'  # Запись сохранится в месте ввода
            vvedeno_luboe = ''
            # continue

        elif vvedeno_luboe == ('6'):
            # Сброс состояния
            print("Сброс состояния до текущего экрана")
            perenos_sostoyaniya()
            schetchik = 0

        elif vvedeno_luboe == ('7'):
            print("Стирание краткосрочной памяти")
            in_pamyat = []
            in_pamyat_name = []

        elif vvedeno_luboe == ('8'):
            # запуск автоматического срабатывания счётчика без нажатия enter
            source = None

        elif vvedeno_luboe == ('9'):
            stiranie_pamyati()
            # source = None
            vvedeno_luboe = ''
            schetchik = 0
            perenos_sostoyaniya()
            posledniy_t_0 = 0
            posledniy_t = old_ekran
            proverka_nalichiya_svyazey_t_t_o()
            posledniy_t = 0

        elif vvedeno_luboe != "":
            bil_klick = False
            print(vvedeno_luboe, '=========================')
            for vvedeno_luboe1 in vvedeno_luboe:
                # 16.06.23 - связываем сущность одной команды с t0, обнуляем tp и t
                # print(f"Рассматривается следующее введённое сообщение: {vvedeno_luboe1}")
                if '.' and 'click' in vvedeno_luboe1:
                    # print(f"Сообщение содержит и точку и click: {vvedeno_luboe1}")
                    # для разрыва сущности, если происходит нажатие кнопок, а затем клик мышкой
                    # Если клик не находится в начале списка - нужно принудительно отделить его от предыдущих сущностей
                    if vvedeno_luboe1 != vvedeno_luboe[0]:
                        # Добавление 'name2' к t0, для возможности отсеивания по этому параметру
                        name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", (posledniy_t,))
                        for name2_1 in name2:
                            # print(f'Найден name2: {name2_1} у точки: {posledniy_t}')
                            new_tochka_time_0 = sozdat_new_tochky('time_0', 0, 'time',
                                                                  "zazech_sosedey", 1, 0, 0,
                                                                  posledniy_t_0, posledniy_t, name2_1[0]+'/t')
                            pereimenovat_name2_y_to(new_tochka_time_0, posledniy_t)
                            print(f'Создана новая точка t0 {new_tochka_time_0} до этого был posl_to = {posledniy_t_0}')
                        sozdat_svyaz(posledniy_t_0, new_tochka_time_0, 1)
                        sozdat_svyaz(posledniy_t, new_tochka_time_0, 1)
                        sozdat_svyaz(new_tochka_time_0, posledniy_tp, 1)  # 21.06.23 была добавлена дублирующая связь с tp (есть ещё одна)
                        posledniy_t_0 = new_tochka_time_0
                        print(f'Posl_t0 из-за ввода изображения стал = {posledniy_t_0}')
                        sozdat_svyaz_s_4_ot_luboy_tochki(posledniy_tp)
                        posledniy_tp = 0
                        posledniy_t = 0
                    for vvedeno_luboe2 in vvedeno_luboe1.split('.'):
                        poisk_bykvi_iz_vvedeno_v2(vvedeno_luboe2)
                    # print(f'Обработка vvedeno_luboe1 ({vvedeno_luboe1})')
                    # 25.09.23 - Добавление 'name2' к t0, для возможности отсеивания по этому параметру
                    name2 = cursor.execute("SELECT name2 FROM tochki WHERE ID = ?", (posledniy_t,))
                    for name2_1 in name2:
                        # print(f'Найден name2: {name2_1} у точки: {posledniy_t}')
                        new_tochka_time_0 = sozdat_new_tochky('time_0', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                                              posledniy_t, name2_1[0]+'/t')
                        pereimenovat_name2_y_to(new_tochka_time_0, posledniy_t)
                        print(f'Создана новая t0: {new_tochka_time_0}')
                    sozdat_svyaz(posledniy_t_0, new_tochka_time_0, 1)
                    sozdat_svyaz(posledniy_t, new_tochka_time_0, 1)
                    sozdat_svyaz(new_tochka_time_0, posledniy_tp, 1)   # 21.06.23 была добавлена дублирующая связь с tp (есть ещё одна)
                    posledniy_t_0 = new_tochka_time_0
                    print(f'Posl_t0 из-за ввода изображения (в конце обработки) стал = {posledniy_t_0}')
                    sozdat_svyaz_s_4_ot_luboy_tochki(posledniy_tp)
                    posledniy_tp = 0
                    posledniy_t = 0
                    bil_klick = True
                else:
                    # print(f'Сообщение не содержит точку или click: {vvedeno_luboe1}')
                    poisk_bykvi_iz_vvedeno_v2(vvedeno_luboe1)
                    bil_klick = False
            # 12.01.23 - Если введено не list (т.е. не содержит клик) - то сохранить во входящих
            # print(f'vvedeno_luboe = {vvedeno_luboe}')
            if not isinstance(vvedeno_luboe, list):
                for vvedeno_luboe_split in vvedeno_luboe.split():
                    print(f"Добавляется в in_pamyat_name {vvedeno_luboe_split}")
                    in_pamyat_name.append(vvedeno_luboe_split)

            print(f'in_pamyat_name содержит следующее: {in_pamyat_name}')
            vvedeno_luboe = ''
            proverka_nalichiya_svyazey_t_t_o()
            functions()
            # 3.2.1 - зафиксировать создание новой сущности, создав связь м/у posl_tp и (4)
            sozdat_svyaz_s_4()

            posledniy_tp = 0
            posledniy_t = 0
            # print("Было введено vvedeno_luboe: ", vvedeno_luboe)
            # schetchik = 0   # 07.11.23 - добавлено обнуление, чтобы не перешло состояние к старому экрану
            source = None

        else:
            if schetchik == 1:
                print(f'in_pamyat сейчас такая: {in_pamyat}')
                if in_pamyat != []:
                    # Вместо моста - зажечь повторно posl_t от первой (in)
                    print(f'Зажигается повторно posl_t, первый в списке: {in_pamyat}')
                    cursor.execute("UPDATE 'tochki' SET work = 1 WHERE ID = ?", (in_pamyat[0],))
                    # 21.12.23 - за основу формирования дерева взята точка time, а не time_0
                    # Найти t от posl_t0
                    poisk_svyazi_t_i_t0 = tuple(cursor.execute("SELECT svyazi.id_start "
                                                                           "FROM svyazi JOIN tochki "
                                                                           "ON svyazi.id_start = tochki.id "
                                                                           "WHERE svyazi.id_finish = ? AND tochki.name = 'time'",
                                                               (posledniy_t_0, )))
                    print(f'Для последующей прошивки найдена следующая time: {poisk_svyazi_t_i_t0}, где posl_t0 = {posledniy_t_0}')
                    if poisk_svyazi_t_i_t0:
                        for poisk_svyazi_t_i_t01 in poisk_svyazi_t_i_t0:
                            # ydalit_svyaz(poisk_svyazi_t_i_t01[0], posledniy_t_0)
                            # sozdat_svyaz(posledniy_t_0, poisk_svyazi_t_i_t01[0], 1)
                            # 21.12.23 - прошивка по дереву будет проходить через time, а не через time_0
                            try:
                                proshivka_po_derevy(poisk_svyazi_t_i_t01[0])   # Добавил передачу in_pamyat для создания цепочки действий
                            except RecursionError:
                                print("!!!!!!!!!!!!!!!!!Произошла ошибка: maximum recursion depth exceeded in comparison!!!!!!!!!!!!!!!!!!")

            elif schetchik >= 10:
                functions()

                schetchik = 0

                perenos_sostoyaniya()   # 30.11.23 - убрано из срабатывания в каждый счётчик

                # 28.11.23 - Если за 10 счётчиков не произошло никаких реакций, действий - то posl_t0 становится
                # old_ekran, а если произошло - продолжаются действия и posl_t0 не изменяется
                t0_10_proverka = posledniy_t_0
                print(f"Изменился ли t0? Текущий posl_t0 = {posledniy_t_0}, t0_proverka = posl_t0 = {t0_10_proverka}, "
                      f"старый t0 (в предыдущем 10м цикле) был = {t0_10}")
                if t0_10_proverka == t0_10:
                    if in_pamyat == 0:
                        posledniy_t_0 = 0
                        posledniy_t = old_ekran
                        proverka_nalichiya_svyazey_t_t_o()
                        posledniy_t = 0
                        posledniy_otvet = 0  # 07.11.23 - раньше последний ответ становился = 0, когда счётчик был = 1.
                        print("")
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                        print(f">>>>>>>>>>>>>>>>>>>>  Переход в posl_t0 = {posledniy_t_0}  <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                        print(f">>>>>>>>>>>>>>>>>>>  Закончилась цепочка действий, началась новая  <<<<<<<<<<<<<<<<<<<<<<<")
                        print('')
                        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                        print("")
                else:
                    t0_10 = t0_10_proverka
                    print("")
                    print("-------------------Состояние posl_to поменялось-------------------------------")
                    print("-------------------Цепочка действий продолжается---------------------------------")
                    print("")
            else:
                functions()

        ymenshenie_signal()

    p1.terminate()