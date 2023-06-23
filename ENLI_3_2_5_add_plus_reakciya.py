from db import Database
from time import sleep

from mous_kb_record import rec, play


cursor = Database('Li_db_v1_4.db')

A = True
posledniy_t = 0
posledniy_t_0 = 3   # переменная содержит ID последней временной точки t0
posledniy_tp = 0
posledniy_otvet = 0

source = None  # Получает значение источника ввода None - клавиатура, 'rec' -  запись клавиатуры и мыши

# print("Posl_to теперь 1 : ", posledniy_t_0)

def stiranie_pamyati():
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp
    # Удаление лишних строчек в таблице точки, где ID>10 - это точка и реакция на 0, которая постоянно записывается.
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM tochki WHERE ID > 10")
    cursor.execute("DELETE FROM svyazi WHERE ID > 15")
    cursor.execute("UPDATE tochki SET puls = 0 AND freq = 10 AND signal = 0 AND work = 0")
    posledniy_t_0 = 3
    posledniy_t = 0
    posledniy_tp = 0



def poisk_bykvi_iz_vvedeno_v2(symbol):   # Функция находит ID у буквы из списка введённых
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp

    # print(f'Передано на обработку следующее: {symbol}')
    nayti_id = cursor.execute("SELECT ID FROM tochki WHERE name = ? AND type = 'mozg'", (symbol, )).fetchone()
    # print("poisk_bykvi_iz_vvedeno_v2. ID у входящей точки такой: ", nayti_id)
    if not nayti_id:
        # print("poisk_bykvi_iz_vvedeno_v2. Такого ID нету")
        new_tochka_name = sozdat_new_tochky(symbol, 0, 'mozg', 'zazech_sosedey', 1, 0, 10, 0, 0, " ")
        # print("Создали новую точку in: ", new_tochka_name)
        new_tochka_print = sozdat_new_tochky(symbol, 0, 'print', "print1", 1, 0, 0, new_tochka_name, 0, " ")
        new_tochka_time_t = sozdat_new_tochky('time', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                              posledniy_t, symbol)
        new_tochka_time_p = sozdat_new_tochky('time_p', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                            posledniy_tp, symbol)
        # нужно создать между ними связь
        sozdat_svyaz(0, new_tochka_time_t, 1)
        sozdat_svyaz(new_tochka_name, new_tochka_time_t, 1)
        sozdat_svyaz(new_tochka_time_t, new_tochka_time_p, 1)
        sozdat_svyaz(new_tochka_time_p, new_tochka_print, 1)
        sozdat_svyaz(new_tochka_name, new_tochka_print, 1)  # 3.2.3 - эта связь нужна, чтобы создавалась сущность (tp)
        if posledniy_t != 0:
            sozdat_svyaz(posledniy_t, new_tochka_time_t, 1)  # weight was 0.1 in 2.3.1
        posledniy_t = new_tochka_time_t
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
                        # print("nayti_svyazi_s_signal_porog2= ", nayti_svyazi_s_signal_porog2)
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
                    # print("Создана новая (т): ", new_t, " где rod1 = ", tochka_1, " и rod2 = ", posledniy_t)
                    sozdat_svyaz(tochka_1, new_t, 1)  # weight was 0.1
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
                            # 3.2.5 - добавлено зажигание (t), после ввода существующего (in)
                            # print('Зажглась (t) от имеющегося (in): ', naydennaya_tochka1)
                            # cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", naydennaya_tochka1)
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
                                        # 3.2.5 - добавлено зажигание (t), после ввода существующего (in), но это (tp) и не должно зажигаться
                                        # print('Зажглась (tp) от имеющегося (in): ', poisk_tp1)
                                        # cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", poisk_tp1)
                                        for poisk_tp2 in poisk_tp1:
                                            posledniy_tp = poisk_tp2


def proverka_nalichiya_svyazey_t_t_o():
    # функция создаёт (new_posl_t_o) между загоревшейся (posledniy_t) и (posledniy_t_0)
    global posledniy_t
    global posledniy_tp
    global posledniy_t_0
    global posledniy_t_0_kortez
    list_poiska_t0 = []
    if posledniy_t != 0:
        # print("proverka_nalichiya_svyazey_t_t_o: posledniy_t_0 = ", posledniy_t_0, ' posledniy_t = ', posledniy_t)
        poisk_svyazi_t_s_t0 = tuple(
            cursor.execute("SELECT ID FROM tochki WHERE rod1 = ? AND name = 'time_0'", posledniy_t_0_kortez))
        # print('poisk_svyazi_t_s_t0 = ', poisk_svyazi_t_s_t0)
        for poisk_svyazi_t_s_t01 in poisk_svyazi_t_s_t0:
            for poisk_svyazi_t_s_t02 in poisk_svyazi_t_s_t01:
                poisk_svyazi_t_s_t03 = tuple(
                    cursor.execute("SELECT ID FROM tochki WHERE ID = ? AND rod2 = ?", (poisk_svyazi_t_s_t02,
                                                                                       posledniy_t)))
                # print('poisk_svyazi_t_s_t03 = ', poisk_svyazi_t_s_t03)
                if poisk_svyazi_t_s_t03 != ():
                    for poisk_svyazi_t_s_t04 in poisk_svyazi_t_s_t03:
                        list_poiska_t0 += poisk_svyazi_t_s_t04
                        # print('list_poiska_t0 = ', list_poiska_t0)
                        for poisk_svyazi_t_s_t05 in poisk_svyazi_t_s_t04:
                            posledniy_t_0 = poisk_svyazi_t_s_t05
                            # print("Posl_to теперь 3 : ", posledniy_t_0)
                            # 3.2.5 - зажигание posl_t0
                            # for posledniy_t_01 in posledniy_t_0:
                            # cursor.execute("UPDATE tochki SET work = 1 WHERE ID = ?", (posledniy_t_0,))

        # print('list_poiska_t0  2 : ', list_poiska_t0)
        if list_poiska_t0 == []:
            new_t0 = sozdat_new_tochky('time_0', 0, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, posledniy_t, " ")
            # print("Создана новая (t0): ", new_t0, " где rod1 = ", posledniy_t_0, " и rod2 = ", posledniy_t)
            sozdat_svyaz(posledniy_t_0, new_t0, 1)  # weight was 0.1
            sozdat_svyaz(posledniy_t, new_t0, 1)  # weight was 0.1
            sozdat_svyaz(new_t0, posledniy_tp, 1)  # 21.06.23 - Добавил дублирующую связь от t0 к tp
            # v3.0.0 - posledniy_t становится новая связующая (.) м/у внешней горящей и старым posledniy_t
            posledniy_t_0 = new_t0
            # print("Posl_to теперь 2 : ", posledniy_t_0)
        posledniy_t = 0
        # posledniy_tp = 0   # 06.03.23 - добавлено


def proverka_signal_porog():
    # print("Работа функции проверка сигнал порог")
    nayti_tochki_signal_porog = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal >= porog"))
    # 2.3.0 - ранее в nayti_tochki_signal_porog искались только (р), теперь сделал, чтобы находились все (...)
    # print("proverka_signal_porog. Нашли точки, у которых signal выше чем porog", nayti_tochki_signal_porog)
    for nayti_tochki_signal_porog1 in nayti_tochki_signal_porog:
        # print("proverka_signal_porog. Нашли точки: ", nayti_tochki_signal_porog1, " у которых сигнал signal выше чем porog")
        # print("zazech_sosedey. Проверка porog, какой у этой точки porog", nayti_tochki_signal_porog_proverka_signal)
        cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_tochki_signal_porog1)
        cursor.execute("UPDATE tochki SET signal = 0.9 WHERE ID = (?)", nayti_tochki_signal_porog1)



def pogasit_vse_tochki():
    # погасить все точки в конце главного цикла
    nayti_ID_s_work = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0"))    #!!! ранее был "AND work= 1"
    # print("погашены все точки: ", nayti_ID_s_work)
    for nayti_ID_s_work_1 in nayti_ID_s_work:
        cursor.execute("UPDATE tochki SET work = 0 WHERE ID = (?)", nayti_ID_s_work_1)
        cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = (?)", nayti_ID_s_work_1)
    nayti_ID_s_work_1 = tuple(cursor.execute("SELECT ID FROM tochki WHERE work > 0"))
    # print("погашены все точки 2: ", nayti_ID_s_work_1)
    for nayti_ID_s_work2 in nayti_ID_s_work_1:
        cursor.execute("UPDATE tochki SET work = 0 WHERE ID = (?)", nayti_ID_s_work2)
        # cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = (?)", nayti_ID_s_work1)


def obnylit_signal_p():
    # обнуляет сигнал у (р), чтобы их не смогли зажечь (т), не являющиеся состоянием
    cursor.execute("UPDATE tochki SET signal = 0 WHERE type = 'print' AND signal > 0")


def pogasit_vse_tochki_t():
    # погасить все точки (t)
    nayti_t_s_work = tuple(cursor.execute("SELECT ID FROM tochki WHERE work = 1 AND type = 'time'"))
    for nayti_t_s_work1 in nayti_t_s_work:
        cursor.execute("UPDATE tochki SET work = 0 WHERE ID = (?)", nayti_t_s_work1)



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
                                cursor.execute("UPDATE tochki SET signal = signal - 1 WHERE ID = ? AND work >= 1", ID)
                                cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = 2")
                                cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 2")
    # гашение точки, которая отработала
    cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", ID)
    cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", ID)
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
    print("\033[31m {}".format(text))
    print("\033[0m {}".format("**********************************"))

    # Воспроизведение событий клавиатуры и мыши.
    # Данные в 1 списке, подрряд для всех событий:
    # Для клавиатуры 2 элемента: 'Key.down'/'Key.up', Клавиша (символ или название)
    # Для мыши 4 элемента: 'Button.down'/'Button.up', 'left'/'right', 'x.y',  'image' (имя изображения элемента)
    # Пример: ['Button.down', 'left', 'elem_230307_144451.png', 'Button.up', 'left', 'Button.down',
    # 'left', 'elem_230228_163525.png', 'Button.up', 'left']
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

        i += 1

def sozdat_svyaz(id_start, id_finish, weight):
    # проверим, есть ли уже такая связь
    proverka_svyazi = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?",
                                           (id_start, id_finish)))
    if proverka_svyazi == ():
        max_ID_svyazi = tuple(cursor.execute("SELECT MAX(ID) FROM svyazi"))
        for max_ID_svyazi1 in max_ID_svyazi:
            old_id_svyazi = max_ID_svyazi1[0]
            new_id_svyazi = old_id_svyazi + 1
        cursor.execute("INSERT INTO svyazi VALUES (?, ?, ?, ?)", (new_id_svyazi, id_start, id_finish, weight))
    else:
        for proverka_svyazi1 in proverka_svyazi:
            cursor.execute("UPDATE svyazi SET weight = weight + 0.1 WHERE ID = ?", proverka_svyazi1)



def sozdat_new_tochky(name, work, type, func, porog, signal, puls, rod1, rod2, freq):
    max_ID = cursor.execute("SELECT MAX(ID) FROM tochki").fetchone()
    new_id = max_ID[0] + 1
    cursor.execute("INSERT INTO tochki VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        new_id, name, work, type, func, porog, signal, puls, rod1, rod2, freq))
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




def ymenshit_svyazi():
    # 2.3.0 - в конце цикла уменьшаем вес связи на 0,01, но если вес не равняется 1.
    cursor.execute("UPDATE svyazi SET weight = weight - 0.005 WHERE weight < 1 AND weight > 0.005")
    # 2.3.0 - если связь ушла в 0 - то она удаляется
    cursor.execute("DELETE FROM svyazi WHERE weight <= 0")



def concentrator_deystviy():
    B = True
    global posledniy_t_0
    global posledniy_otvet
    global schetchik

    list_otric_reac = []
    list_deystviy = []
    # 3.2.4 - соединение вместе и горящих и не горящих (tp) с последующим перебором вариантов
    list_tp = []
    list_signal_tp = []
    list_isklucheniya_deystviy = []
    poisk_drygih_tp = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0 AND name = 'time_p'"))
    print("Нашли следующие возможные (tp), у которых signal > 0 AND name = 'time_p': ", poisk_drygih_tp)
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
                list_svyazi_s_posl_t0 = []
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
                            cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", poisk_tp)
                    else:
                        # Проверка - имеется ли связь с posl_t0 и найденным t0
                        for list_t01 in list_t0:
                            list_t01_kortez = (list_t01, )
                            # print('Поиск связи между posledniy_t_0 = ', posledniy_t_0, 'и list_t01 = ', list_t01)
                            poisk_svyazi_s_posl_t0 = tuple(
                                cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = ?",
                                               (posledniy_t_0, list_t01)))
                            # print('poisk_svyazi_s_posl_t0 = ', poisk_svyazi_s_posl_t0)
                            # не ищется ID... разделяю на 2 фильтр
                            if poisk_svyazi_s_posl_t0 != ():
                                for poisk_svyazi_s_posl_t01 in poisk_svyazi_s_posl_t0:
                                    for poisk_svyazi_s_posl_t02 in poisk_svyazi_s_posl_t01:
                                        poisk_svyazi_s_posl_t03 = tuple(
                                            cursor.execute("SELECT ID FROM svyazi WHERE id_finish = ? AND ID = ?",
                                                           (list_t01, poisk_svyazi_s_posl_t02)))
                                        # print('poisk_svyazi_s_posl_t03 = ', poisk_svyazi_s_posl_t03)
                                        if poisk_svyazi_s_posl_t03 != ():
                                            # 3.2.5 - если имеется у этой tp связь с posl_to - это нужно зафиксировать,
                                            # чтобы другие связи не попали в лист действий
                                            list_svyazi_s_posl_t0 += poisk_svyazi_s_posl_t03
                                            # а если связь есть - то нужно проверить имеются ли реакции на данное действие (ответ)
                                            poisk_svyazi_s_reakciey = tuple(
                                                cursor.execute("SELECT id_finish FROM svyazi WHERE id_start = ?",
                                                               list_t01_kortez))
                                            # print('Поиск связи с реакцией: ', poisk_svyazi_s_reakciey)
                                            for poisk_svyazi_s_reakciey1 in poisk_svyazi_s_reakciey:
                                                # print('poisk_svyazi_s_reakciey1 = ', poisk_svyazi_s_reakciey1)
                                                if poisk_svyazi_s_reakciey1 == (2,):
                                                    # если найдена (-) реакция - то не нужно применять это действие.
                                                    # запустить обратный сбор сущности tp и зажигание с первой (.)
                                                    list_otric_reac += poisk_svyazi_s_reakciey1
                                                    # print('Лист отрицательных связей такой: list_otric_reac', list_otric_reac)
                                                    print('Найдена отрицательная реакция и действие отменено: ', poisk_tp)
                                                    list_isklucheniya_deystviy += poisk_tp
                                                    # 3.2.1 - погасить отработанные (...)
                                                    cursor.execute("UPDATE tochki SET work = 0 AND signal = 0 WHERE ID = ?",
                                                                   poisk_tp)
                                                elif poisk_svyazi_s_reakciey1 == (1, ):
                                                    # если нашлась (+) реакция - то нужно применить именно это действие
                                                    list_deystviy = []
                                                    list_deystviy += poisk_tp
                                                    print(f'Найдена положительная реакция и действие применено: '
                                                          f'{poisk_tp}. Остальные точки погашены')
                                                    pogasit_vse_tochki()
                                                    B = False
                                                else:
                                                    # если нет связи с (+-), но имеется связь с posl_t0 - нужно добавить
                                                    # это действие в начало листа действий
                                                    list_deystviy.insert(0, poisk_tp[0])
                            else:
                                list_deystviy += poisk_tp
                                # print('List_deystviy 4 стал следующим: ', list_deystviy)
                        # 3.2.5 - если tp не применялось и нет опыта - то добавить его в лист действий
                        if list_otric_reac == []:
                            list_deystviy += poisk_tp
                            # print('List_deystviy 2 стал следующим: ', list_deystviy)
                            # 3.2.5 - возможно проверки на отсутствие отрицательных реакций будет достаточно, чтобы не
                            # дублировать действия
                            # if list_svyazi_s_posl_t0 == []:
                            #     list_deystviy += poisk_tp
                            #     print('List_deystviy 5 стал следующим: ', list_deystviy)
                else:
                    B = False
                schetchik_B += 1
    # print(f'list_isklucheniya_deystviy = {list_isklucheniya_deystviy}')
    for value in list_isklucheniya_deystviy:
        while value in list_deystviy:
            list_deystviy.remove(value)
    # Удаление дублей из листа действий
    list_deystviy = list(set(list_deystviy))
    print('Лист действий: ', list_deystviy)
    if list_deystviy != []:   # 3.2.3 - было if posl_tp != ()
        list_minus_deystviy = []
        otmena_minus_deystviya = 0    #переменная, чтобы не происходил ответ, если он уже имеется
        # 13.02.23 - добавляю поиск отрицательных реакций у найденных действий, чтобы снизить возможность повторного
        # не верного ответа
        for list_deystviy1 in list_deystviy:
            # поиск связей с текущим ID (tp) и (t0)
            # print("Лист действий, такой ID передаётся: ", list_deystviy1)
            # print("otmena_minus_deystviya: ", otmena_minus_deystviya)
            if otmena_minus_deystviya != 1:
                # приходится ID передавать в кортеже
                list_deystviy1_kortez = (list_deystviy1,)
                # # 16.03.23 - добавил гашение этой точки действия, чтобы убрать повторы
                # cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = ?", list_deystviy1_kortez)
                # cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", list_deystviy1_kortez)
                poisk_svyazi_ID_s_t0 = tuple(cursor.execute("SELECT ID FROM tochki WHERE rod2 = ? AND name = 'time_0'",
                                                               list_deystviy1_kortez))
                # print("Найдены следующие связи (tp): ", list_deystviy1, " и (to): ", poisk_svyazi_ID_s_t0)
                # найдём связи с (+)-реакцией, если имеются связи с (t0), а если не имеются - то применим это действие:
                if poisk_svyazi_ID_s_t0 != ():
                    for poisk_svyazi_ID_s_t01 in poisk_svyazi_ID_s_t0:
                        poisk_svyazi_t0_s_reakciey = tuple(cursor.execute(
                            "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 1", poisk_svyazi_ID_s_t01))
                        # print("Найдены связи (t0) и (+): ", poisk_svyazi_t0_s_reakciey)
                        # если есть связь с (+) - то применим это действие
                        if poisk_svyazi_t0_s_reakciey != ():
                            print("Найдена связь с (+) - значит применяется действие: ", list_deystviy1)
                            sbor_deystviya(list_deystviy1)
                            otmena_minus_deystviya = 1
                            break   # прекращение цикла
                        # если связи с (+) нет - то ищем связь с (-)
                        poisk_svyazi_t0_s_minus = tuple(cursor.execute(
                            "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 2", poisk_svyazi_ID_s_t01))
                        # если связи с (-) нет - то применим это действие, а если есть - то впишем его в список
                        # print("Найдены ли связи с (-): ", poisk_svyazi_t0_s_minus)
                        if poisk_svyazi_t0_s_minus != ():
                            # если были найдены связи с (-)
                            list_minus_deystviy += list_deystviy1_kortez
                    if list_minus_deystviy == []:
                        if otmena_minus_deystviya != 1:
                            print("Не найдена связь с (-) - значит применяется действие: ", list_deystviy1)
                            sbor_deystviya(list_deystviy1)
                            otmena_minus_deystviya = 1
                            break
                else:
                    # из листа действий убирается найденные раньше уже совершаемые действия от текущего (t0), т.е.
                    # исключается полное повторение
                    sbor_deystviya(list_deystviy1)
                    otmena_minus_deystviya = 1
                    break
        # если цикл дошёл до этой строчки - значит не были найдены (tp) с (+) или без связи с (-) и применяется первая
        # из (tp), связанная с (-)
        # print("otmena_minus_deystviya == ", otmena_minus_deystviya)
        if otmena_minus_deystviya != 1:
            if list_minus_deystviy != []:
                print('list_minus_deystviy = ', list_minus_deystviy)
                for value in list_isklucheniya_deystviy:
                    while value in list_minus_deystviy:
                        list_minus_deystviy.remove(value)
                print(f'А стал такой: {list_deystviy}')
                if len(list_minus_deystviy) != 0:
                    sbor_deystviya(list_minus_deystviy[0])
                # else:
                #     for list_minus_deystviy1 in list_minus_deystviy:
                #         sbor_deystviya(list_minus_deystviy1)
        # pogasit_vse_tochki()


def create_dict(point_list, work_dict=dict()):
    """ Рекурсивная функция получающая все связи в виде словаря из БД """
    for point in point_list:
        # Выбрать id_finish из связей, где id_finish = ID в табл. точки и id_start = point и name = time_0.
        points = cursor.execute(
            "SELECT svyazi.id_finish "
            "FROM svyazi JOIN tochki "
            "ON svyazi.id_finish = tochki.id "
            "WHERE svyazi.id_start = ? AND tochki.name = 'time_0'", (point,)).fetchall()
        nodes = [row[0] for row in points]
        if nodes:
            work_dict[point] = nodes
            create_dict(work_dict[point], work_dict)
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


def proshivka_po_derevy():
    """ Проверка возможности применения действий по пути из дерева."""
    global posledniy_t_0
    tree = []
    tree = create_dict([posledniy_t_0])  # Получаем выборку связей в виде словаря (дерево)
    vozmozhnie_deystviya = []
    otricatelnie_deystviya = []
    # print(tree)
    print("Возможный путь действий: ", all_paths(tree, posledniy_t_0))
    # Проверка имеется ли связь с 1 или 2 у точек на пути
    found = False
    for path in all_paths(tree, posledniy_t_0):
        if len(path) > 1:
            # print(f'Проверка пути: {path}, 2я точка такая: {path[1]}')
            svyaz_s_1 = []
            svyaz_s_2 = []
            for tochka in path:
                # print(f'Рассматриваем точку: {tochka}')
                proverka_nalichiya_svyazi_s_1 = tuple(cursor.execute(
                    "SELECT id_start FROM svyazi WHERE id_finish = 1 AND id_start = ?", (tochka,)))
                # print(f'Нашли следующие связи c 1: {proverka_nalichiya_svyazi_s_1}')
                for proverka_nalichiya_svyazi_s_1_1 in proverka_nalichiya_svyazi_s_1:
                    # print(f'Присоединение к svyaz_s_1: {proverka_nalichiya_svyazi_s_1_1[0]}')
                    svyaz_s_1.append(proverka_nalichiya_svyazi_s_1_1[0])
                proverka_nalichiya_svyazi_s_2 = tuple(cursor.execute(
                    "SELECT id_start FROM svyazi WHERE id_finish = 2 AND id_start = ?", (tochka,)))
                # print(f'Нашли следующие связи c 2: {proverka_nalichiya_svyazi_s_2}')
                for proverka_nalichiya_svyazi_s_2_1 in proverka_nalichiya_svyazi_s_2:
                    # print(f'Присоединение к svyaz_s_2: {proverka_nalichiya_svyazi_s_2_1[0]}')
                    svyaz_s_2.append(proverka_nalichiya_svyazi_s_2_1[0])
                    # если была найдена отрицательная реакция и эта точка является второй в пути
                    if proverka_nalichiya_svyazi_s_2_1[0] == path[1]:
                        # print(f'Добавилось отрицательное действие- т.к. оно второе в пути: {proverka_nalichiya_svyazi_s_2_1}')
                        otricatelnie_deystviya.append(proverka_nalichiya_svyazi_s_2_1[0])
            if svyaz_s_1 and not svyaz_s_2:
                # Если имеется связь с (+) - то применить этот путь
                poisk_tp_v_pervoy_tochke_pyti = tuple(cursor.execute("SELECT svyazi.id_finish "
                "FROM svyazi JOIN tochki "
                "ON svyazi.id_finish = tochki.id "
                "WHERE svyazi.id_start = ? AND tochki.name = 'time_p'", (path[1],)))
                # print(f'Применить действие, если t0 - start: {poisk_tp_v_pervoy_tochke_pyti}')
                if poisk_tp_v_pervoy_tochke_pyti:
                    for poisk_tp_v_pervoy_tochke_pyti1 in poisk_tp_v_pervoy_tochke_pyti:
                        sbor_deystviya(poisk_tp_v_pervoy_tochke_pyti1[0], path[1])
                        found = True   # выход из внешнего цикла
                        break
                else:
                    # Если нет связи, где t0 - старт, то возможно имеется связь, где эта t0- финиш
                    poisk_tp_v_pervoy_tochke_pyti_fin = tuple(cursor.execute(
                        "SELECT svyazi.id_start "
                         "FROM svyazi JOIN tochki "
                         "ON svyazi.id_start = tochki.id "
                         "WHERE svyazi.id_finish = ? AND tochki.name = 'time_p'",
                         (path[1],)))
                    print(f'Применить действие, если t0 - finish: {poisk_tp_v_pervoy_tochke_pyti_fin}')
                    if poisk_tp_v_pervoy_tochke_pyti_fin:
                        for poisk_tp_v_pervoy_tochke_pyti_fin1 in poisk_tp_v_pervoy_tochke_pyti_fin:
                            sbor_deystviya(poisk_tp_v_pervoy_tochke_pyti_fin1[0], path[1])
                            found = True  # выход из внешнего цикла
                            break
            else:
                # Добавить вторую точку в возможные действия
                vozmozhnie_deystviya.append(path[1])
            if found:
                break  # выход из внешнего цикла

    # Если алгоритм дошёл до сюда - значит не был найден удовлетворительный путь - применить первое действие из возможных
    found1 = False
    print(f'Возможные действия: {vozmozhnie_deystviya}')
    if vozmozhnie_deystviya:
        for vozmozhnie_deystviya1 in vozmozhnie_deystviya:
            # Проверить является ли эта точка отрицательной.
            print(f'Проверка имеется ли возможное действие ({vozmozhnie_deystviya1}) в списке отрицательных: {otricatelnie_deystviya}')
            if not vozmozhnie_deystviya1 in otricatelnie_deystviya:
                print(f'Применить возможное действие: {vozmozhnie_deystviya1}')
                poisk_tp_v_pervoy_tochke_pyti = tuple(cursor.execute("SELECT svyazi.id_finish "
                                                                     "FROM svyazi JOIN tochki "
                                                                     "ON svyazi.id_finish = tochki.id "
                                                                     "WHERE svyazi.id_start = ? AND tochki.name = 'time_p'",
                                                                     (vozmozhnie_deystviya1,)))
                # print(f'Применить действие, если t0 - start: {poisk_tp_v_pervoy_tochke_pyti}')
                if poisk_tp_v_pervoy_tochke_pyti:
                    for poisk_tp_v_pervoy_tochke_pyti1 in poisk_tp_v_pervoy_tochke_pyti:
                        sbor_deystviya(poisk_tp_v_pervoy_tochke_pyti1[0], vozmozhnie_deystviya1)
                        found1 = True
                        break
                else:
                    # Если нет связи, где t0 - старт, то возможно имеется связь, где эта t0- финиш
                    poisk_tp_v_pervoy_tochke_pyti_fin = tuple(cursor.execute(
                        "SELECT svyazi.id_start "
                        "FROM svyazi JOIN tochki "
                        "ON svyazi.id_start = tochki.id "
                        "WHERE svyazi.id_finish = ? AND tochki.name = 'time_p'",
                        (vozmozhnie_deystviya1,)))
                    # print(f'Применить действие, если t0 - finish: {poisk_tp_v_pervoy_tochke_pyti_fin}')
                    if poisk_tp_v_pervoy_tochke_pyti_fin:
                        for poisk_tp_v_pervoy_tochke_pyti_fin1 in poisk_tp_v_pervoy_tochke_pyti_fin:
                            sbor_deystviya(poisk_tp_v_pervoy_tochke_pyti_fin1[0], vozmozhnie_deystviya1)
                            found1 = True
                            break
            else:
                print(f'Запущена функция Концентратор действий, т.к. все возможные действия - отрицательные')
                concentrator_deystviy()
                break
            if found1:
                break
    else:
        # не было найдено продолжения - запустить поиск из горящих (tp)
        print(f'Запущена функция Концентратор действий')
        concentrator_deystviy()

def sbor_deystviya(tp, t0=None):
    # собирает в обратном порядке сущность от последнего tp и приводит в действие ответ
    print("Разбирается следующий tp для ответа: ", tp)
    global posledniy_t_0
    global posledniy_otvet
    B = True
    tp_kortez = (tp, )

    # 22.06.23 - гашение ответов, для блокировки повторов.
    cursor.execute("UPDATE tochki SET work = 0 AND signal = 0 WHERE ID = ?", (tp,))

    #14.06.23 - ввод запоминания последнего ответа, для блокирования повторов
    posledniy_otvet = tp
    # print(f'Последний ответ стал равен: {posledniy_otvet}')

    # 3.2.2 - добавляется поиск уже имеющегося t0 и проверяется - имеется ли связь с posl_t0
    poisk_svyazi_tp_s_t0 = tuple(cursor.execute("SELECT ID FROM tochki WHERE rod1 = ? AND name = 'time_0' AND rod2 = ?",
                                                (posledniy_t_0, tp)))
    # 22.06.23 - если передаётся t0 - то он и становится posl_t0
    if t0:
        posledniy_t_0 = t0
    else:
        if poisk_svyazi_tp_s_t0 == ():
            # создать t0 и к нему привязать tp
            new_tochka_t0 = sozdat_new_tochky('time_0', 0, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, tp, " ")
            # print(f'new_tochka_t0 такая: {new_tochka_t0}, а была posl_t0 = {posledniy_t_0}')
            # sozdat_svyaz(new_tochka_t0, tp, 1)  # 3.2.2 - убрал обратную связь
            sozdat_svyaz(posledniy_t_0, new_tochka_t0, 1)
            sozdat_svyaz(new_tochka_t0, tp, 1)
            posledniy_t_0 = new_tochka_t0
            # print("Posl_to теперь 5 : ", posledniy_t_0)
        else:
            for poisk_svyazi_tp_s_t01 in poisk_svyazi_tp_s_t0:
                for poisk_svyazi_tp_s_t02 in poisk_svyazi_tp_s_t01:
                    posledniy_t_0 = poisk_svyazi_tp_s_t02
                    # print("Posl_to теперь 6 : ", posledniy_t_0)
                    # cursor.execute("UPDATE tochki SET work = 1 WHERE ID = ?", (posledniy_t_0,))
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
    # функция находит все (.), где сигнал более 0 и уменьшает на 0,1
    # ymenshenie_signal_ = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal >= 0.1",))
    cursor.execute("UPDATE tochki SET signal = signal - 0.1 WHERE signal >= 0.1 AND signal < 1")
    cursor.execute("UPDATE tochki SET signal = signal - 0.01 WHERE signal >= 0 AND signal < 0.1")  #3.2.4 - added
    # print("Уменьшен сигнал у следующих точек: ", ymenshenie_signal_)


schetchik = 0

while A:
    if rec.status:
        # Блокируем основную программу, пока идет запись
        sleep(0.001)
        continue

    schetchik += 1
    print('************************************************************************')
    print("schetchik = ", schetchik)
    posledniy_t_0_kortez = (posledniy_t_0,)
    proverka_signal_porog()   # проверка и зажигание точек, если signal >= porog
    # concentrator_deystviy()
    proshivka_po_derevy()

    # 14.06.23 - возврат к необходимости нажимать enter на каждом цикле
    vvedeno_luboe = input("Введите текст: ")

    # print("Сейчас ", source)
    # if source == 'input':
    # # Ввод строки с клаиатуры, запись побуквенно
    #     vvedeno_luboe = input("Введите текст: ")

    if source == 'rec':
        # Источник события мыши и клавиатуры. Чтение из объекта rec
        # Формат записи
        # Для клавиатуры: 'Key.down'/'Key.up', Клавиша (символ или название)
        # Для мыши: 'Button.down'/'Button.up', 'left'/'right', 'x.y', 'image' (имя изображения элемента)

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
                if event['event'] == 'down':
                    vvedeno_luboe.append('position.' + str(event['x']) + '.' + str(event['y']))
                    vvedeno_luboe.append('image.' + str(event['image']))
                vvedeno_luboe.append('Button.' + event['event'] + '.' + event['key'].split('.')[1])

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
        # sleep(1)
    print("")

    # print('ввели: ', vvedeno_luboe)
    if vvedeno_luboe == ('0'):
        A = False

    if vvedeno_luboe == ('3'):
        # Включение записи
        cursor.commit()  # Сохраняем изменения в БД
        sleep(1)
        rec.start()
        # source = None  # Запись сохранится в месте ввода
        continue

    if vvedeno_luboe == ('4'):
        # Показать запись
        sleep(1)
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

    if vvedeno_luboe == ('5'):
        # Сохранение записи
        source = 'rec'  # Запись сохранится в месте ввода
        vvedeno_luboe = ''
        # continue

    elif vvedeno_luboe == ('9'):
        stiranie_pamyati()
        source = None
        vvedeno_luboe = ''

    elif vvedeno_luboe == ('2'):
        # нужно проверить имеется ли уже связь м/у t0 и tp
        print("Состояние перед (-) реакцией было такое: ", posledniy_t_0, "    С ней и создаётся связь")
        poisk_svyazi_t0_s_2 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 2",
                                                   posledniy_t_0_kortez))
        if poisk_svyazi_t0_s_2 == ():
            sozdat_svyaz(posledniy_t_0, 2, 1)
        pogasit_vse_tochki()
        source = None
        vvedeno_luboe = ''

    elif vvedeno_luboe == ('1'):
        # нужно проверить имеется ли уже связь м/у t0 и tp
        print("Состояние перед (+) реакцией было такое: ", posledniy_t_0, "    С ней и создаётся связь")
        poisk_svyazi_t0_s_2 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 1",
                                                   posledniy_t_0_kortez))
        if poisk_svyazi_t0_s_2 == ():
            sozdat_svyaz(posledniy_t_0, 1, 1)
        # pogasit_vse_tochki()
        source = None
        vvedeno_luboe = ''

    elif vvedeno_luboe != "":
        print(vvedeno_luboe, '=========================')
        for vvedeno_luboe1 in vvedeno_luboe:
            # 16.06.23 - связываем сущность одной команды с t0, обнуляем tp и t
            if '.' in vvedeno_luboe1:
                for vvedeno_luboe2 in vvedeno_luboe1.split('.'):
                    poisk_bykvi_iz_vvedeno_v2(vvedeno_luboe2)
                # print(f'Обработка vvedeno_luboe1 ({vvedeno_luboe1})')
                new_tochka_time_0 = sozdat_new_tochky('time_0', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                                      posledniy_t, '')
                # print(f'Создана новая t0: {new_tochka_time_0}')
                sozdat_svyaz(posledniy_t_0, new_tochka_time_0, 1)
                sozdat_svyaz(posledniy_t, new_tochka_time_0, 1)
                sozdat_svyaz(new_tochka_time_0, posledniy_tp, 1)
                posledniy_t_0 = new_tochka_time_0
                sozdat_svyaz_s_4_ot_luboy_tochki(posledniy_tp)
                posledniy_tp = 0
                posledniy_t = 0
            else:
                poisk_bykvi_iz_vvedeno_v2(vvedeno_luboe1)

        vvedeno_luboe = ''
        proverka_nalichiya_svyazey_t_t_o()
        functions()
        # 3.2.1 - зафиксировать создание новой сущности, создав связь м/у posl_tp и (4)
        sozdat_svyaz_s_4()
        posledniy_tp = 0
        posledniy_t = 0
        # print("Было введено vvedeno_luboe: ", vvedeno_luboe)
        schetchik = 0
    else:
        if schetchik >= 10:
            # 2.2.2: зажигается in0, которая горит, если нет вх. сигналов
            cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 3")
            functions()
            schetchik = 0
            posledniy_t_0 = 3
            # print("Posl_to теперь 4 : ", posledniy_t_0)
            print("-----------------------------------Переход в (3)-------------------------------------")
        elif schetchik == 1:
            posledniy_otvet = 0
        else:
            functions()
    ymenshenie_signal()


# import diagram
# Диаграмма не работает