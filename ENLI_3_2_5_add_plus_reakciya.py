# 3.2.5 - Добавлена (+) реакция, и уменьшение сигнала на 0,01, если сигнал <0,1


import sqlite3, random
from time import sleep
from mous_kb_record import rec, play



conn = sqlite3.connect('Li_db_v1_4.db')
cursor = conn.cursor()
A = True
posledniy_t = 0
posledniy_t_0 = 3   # переменная содержит ID последней временной точки t0
posledniy_tp = 0
# print("Posl_to теперь 1 : ", posledniy_t_0)

def stiranie_pamyati():
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp
    # удаление лишних строчек в таблице точки, где ID>5. 5 - это последняя (.) реакции "хоро"
    print("Запущено стирание памяти")
    cursor.execute("DELETE FROM tochki WHERE ID > 4")
    cursor.execute("DELETE FROM svyazi WHERE ID > 2") # удаление лишних строчек в таблице связи, где ID>2. 2 - это связь м/у 5 и 1.
    cursor.execute("UPDATE tochki SET puls = 0 AND freq = 10 AND signal = 0 AND work = 0")
    posledniy_t_0 = 3
    posledniy_t = 0
    posledniy_tp = 0



def poisk_bykvi_iz_vvedeno_v2(symbol):   # Функция находит ID у буквы из списка введённых
    global posledniy_t
    global posledniy_t_0
    global posledniy_tp
    nayti_id = tuple(cursor.execute("SELECT ID FROM tochki WHERE name = ? AND type = 'mozg'", symbol))
    # print("poisk_bykvi_iz_vvedeno_v2. ID у входящей точки такой: ", nayti_id)
    if nayti_id == ():
        # print("poisk_bykvi_iz_vvedeno_v2. Такого ID нету")
        new_tochka_name = sozdat_new_tochky(symbol, 0, 'mozg', 'zazech_sosedey', 1, 0, 10, 0, 0, 10)
        new_tochka_print = sozdat_new_tochky(symbol, 0, 'print', "print1", 1, 0, 0, new_tochka_name, 0, 10)
        new_tochka_time_t = sozdat_new_tochky('time', 1, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                              posledniy_t, 10)
        new_tochka_time_p = sozdat_new_tochky('time_p', 0, 'time', "zazech_sosedey", 1, 0, 0, posledniy_t_0,
                                            posledniy_tp, 10)
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
    else:   # если есть такая буква с таким ID
        for nayti_id1 in nayti_id:
            # print("Такая точка уже была введена ранее, ID такой: ", nayti_id1)
            cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_id1)
            # cursor.execute("UPDATE tochki SET puls = 10 WHERE ID = (?)", nayti_id1)
            # cursor.execute("UPDATE tochki SET freq = 10 WHERE ID = (?)", nayti_id1)
            for nayti_id2 in nayti_id1:
                # print("posl_t был: ", posledniy_t)
                proverka_nalichiya_svyazey_in(nayti_id2)



def proverka_nalichiya_svyazey_in(tochka_1):
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
                    new_t = sozdat_new_tochky('time', 0, 'time', 'zazech_sosedey', 1, 0, 0,
                                              tochka_1, posledniy_t, 10)
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
                                new_tp = sozdat_new_tochky('time_p', 1, 'time', 'zazech_sosedey', 1, 0, 0, poisk_p2,
                                                           posledniy_tp, 10)
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
                            cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", naydennaya_tochka1)
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
                            print("Posl_to теперь 3 : ", posledniy_t_0)
                            # 3.2.5 - зажигание posl_t0
                            # for posledniy_t_01 in posledniy_t_0:
                            cursor.execute("UPDATE tochki SET work = 1 WHERE ID = ?", (posledniy_t_0,))

        # print('list_poiska_t0  2 : ', list_poiska_t0)
        if list_poiska_t0 == []:
            new_t = sozdat_new_tochky('time_0', 1, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, posledniy_t, 10)
            # print("Создана новая (т): ", new_t, " где rod1 = ", posledniy_t_0, " и rod2 = ", posledniy_t)
            sozdat_svyaz(posledniy_t_0, new_t, 1)  # weight was 0.1
            sozdat_svyaz(posledniy_t, new_t, 1)  # weight was 0.1
            # v3.0.0 - posledniy_t становится новая связующая (.) м/у внешней горящей и старым posledniy_t
            posledniy_t_0 = new_t
            print("Posl_to теперь 2 : ", posledniy_t_0)
        posledniy_t = 0




def proverka_signal_porog():
    # 2.3.0 - убрана зависимость от пульсации, т.к. отключена пульсация
    # print("Работа функции проверка сигнал порог")
    nayti_tochki_signal_porog = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal >= porog"))
    # 2.3.0 - ранее в nayti_tochki_signal_porog искались только (р), теперь сделал, чтобы находились все (...)
    # print("zazech_sosedey. Нашли точки, у которых signal выше чем porog", nayti_tochki_signal_porog)
    for nayti_tochki_signal_porog1 in nayti_tochki_signal_porog:
        # nayti_tochki_signal_porog_proverka_signal = tuple(
        # cursor.execute("SELECT signal FROM tochki WHERE ID = ?", nayti_tochki_signal_porog1))
        # print("proverka_signal_porog. Нашли точки: ", nayti_tochki_signal_porog1, " у которых сигнал signal выше чем porog")
        # print("zazech_sosedey. Проверка porog, какой у этой точки porog", nayti_tochki_signal_porog_proverka_signal)
        cursor.execute("UPDATE tochki SET work = 1 WHERE ID = (?)", nayti_tochki_signal_porog1)
        cursor.execute("UPDATE tochki SET signal = 0.9 WHERE ID = (?)", nayti_tochki_signal_porog1)
        # cursor.execute("UPDATE tochki SET puls = 10 WHERE ID = (?)", nayti_tochki_signal_porog1)
        # cursor.execute("UPDATE tochki SET freq = 10 WHERE ID = (?)", nayti_tochki_signal_porog1)
        # 2.3.2 - создаётся связь только между (posl_t) и (p) и в другой функции
        # for nayti_tochki_signal_porog2 in nayti_tochki_signal_porog1:
        #     if nayti_tochki_signal_porog2 != posledniy_t:
        #         # проверить имеется ли прямая связь между posledniy_t и этой загоревшейся (т)
        #         proverka_nalichiya_svyazey(nayti_tochki_signal_porog2)



def pogasit_vse_tochki():
    # погасить все точки в конце главного цикла
    nayti_ID_s_work = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0"))
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
    nayti_id_svyaz = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ?", ID))
    # print("deystviye. Список связей у горящей точки: ", nayti_id_svyaz)
    if nayti_id_svyaz != ():  # если список связей не пустой - то идём дальше
        for nayti_id_svyaz1 in nayti_id_svyaz:
            # Найти вес связей
            ves_svyazi = tuple(cursor.execute("SELECT weight FROM svyazi WHERE ID = ?", nayti_id_svyaz1))
            for ves_svyazi1 in ves_svyazi:
                for ves_svyazi2 in ves_svyazi1:
                    # 2.3.0 - сигнал передаётся с уменьшением на вес связи
                    id_tochki_soseda = tuple(cursor.execute("SELECT id_finish FROM svyazi WHERE ID = ?",
                                                            nayti_id_svyaz1))
                    for id_tochki_soseda1 in id_tochki_soseda:
                        for id_tochki_soseda2 in id_tochki_soseda1:
                            cursor.execute("UPDATE tochki SET signal = signal + ? WHERE ID = ?",
                                           (ves_svyazi2, id_tochki_soseda2))
                            # 2.3.0 - если сигнал стал больше, чем порог - то прибавим к связи +вес
                            prov_tochki = tuple(cursor.execute("SELECT signal FROM tochki WHERE ID = ? AND signal >= 1",
                                                               nayti_id_svyaz1))
                            # print('Сигнал у (.), которой передали сигнал такой: ', prov_tochki, ' должен быть больше 1')
                            # Если такая (.) нашлась - значит её сигнал выше, чем 1 (стандартный порог).
                            if prov_tochki != ():
                                cursor.execute("UPDATE svyazi SET weight = weight + 0.01 WHERE ID = ? AND weight < 1",
                                               nayti_id_svyaz1)
                        # если зажглись (+-) - то нужно сразу же провести работу с сигналом (т)
                        for id_tochki_soseda3 in id_tochki_soseda1:
                            # Слишком много происходит ответов из-за того, что (+) передаёт такой мощный сигнал (+1)
                            # if id_tochki_soseda3 == 1:
                            #     # если 1 - то это (+) реакция - прибавим +1 к сигналу (т), чтобы загорелась в след. раз
                            #     cursor.execute("UPDATE tochki SET signal = signal + 1 WHERE ID = ? AND work >= 1", ID)
                            #     cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = 1")
                            #     cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 1")
                            if id_tochki_soseda3 == 2:
                                # если 2 - это (-) реакция - отнимем -1 от сигнала (т), чтобы в след. раз не загорелась
                                cursor.execute("UPDATE tochki SET signal = signal - 1 WHERE ID = ? AND work >= 1", ID)
                                cursor.execute("UPDATE tochki SET signal = 0 WHERE ID = 2")
                                cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 2")
    # гашение точки, которая отработала
    cursor.execute("UPDATE tochki SET work = 0 WHERE ID = ?", ID)



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
    print("\033[31m {}".format(' '))
    print("\033[31m {}".format(text))
    print("\033[0m {}".format(""))



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
    max_ID = tuple(cursor.execute("SELECT MAX(ID) FROM tochki"))
    for max_ID1 in max_ID:
        old_id = max_ID1[0]
        new_id = old_id + 1
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
    # функция для поиска горящих (tp), которые должны быть проверены на возможность действия в первую очередь
    # 1. Находятся горящие (tp)
    # 2. Эти (tp) отсеиваются, если не имеют связи с (t0)
    # 3. Проверка имеется ли связь между t0 от in и t0 от tp
    # 4. Если имеется - проверить есть ли связь с (-)
    global posledniy_t_0
    posledniy_t_0_kortez = (posledniy_t_0, )
    list_otric_reac = []
    list_deystviy = []
    # 3.2.4 - соединение вместе и горящих и не горящих (tp) с последующим перебором вариантов
    list_tp = []
    list_signal_tp = []
    poisk_drygih_tp = tuple(cursor.execute("SELECT ID FROM tochki WHERE signal > 0 AND name = 'time_p'"))
    # print("Нашли следующие возможные (tp), у которых signal > 0 AND name = 'time_p': ", poisk_drygih_tp)
    if poisk_drygih_tp != ():
        for poisk_drygih_tp1 in poisk_drygih_tp:
            # найдём signal у этих (tp)
            list_tp += poisk_drygih_tp1
            poisk_signal_tp = tuple(cursor.execute("SELECT signal FROM tochki WHERE ID = ?", poisk_drygih_tp1))
            # print("Сигнал у tp следующий: ", poisk_signal_tp)
            for poisk_signal_tp1 in poisk_signal_tp:
                list_signal_tp += poisk_signal_tp1
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
                            cursor.execute("SELECT ID FROM svyazi WHERE id_start = ?", posledniy_t_0_kortez))
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
                                                # print('Найдена отрицательная реакция и действие отменено: ', poisk_tp)
                                                # 3.2.1 - погасить отработанные (...)
                                                cursor.execute("UPDATE tochki SET work = 0 AND signal = 0 WHERE ID = ?",
                                                               poisk_tp)
                                            elif poisk_svyazi_s_reakciey1 == (1, ):
                                                # если нашлась (+) реакция - то нужно применить именно это действие
                                                list_deystviy = []
                                                list_deystviy += poisk_tp
                                                # print('Найдена положительная реакция и действие применено: ', poisk_tp)
                                                pogasit_vse_tochki()
                                                B = False
                                        # 3.2.5 - убрал - т.к. действия могут попасть в лист до того, как найдётся
                                        # связь с (-)
                                        # print('Лист отрицательных реакций равен: ', list_otric_reac)
                                        # if list_otric_reac == []:
                                        #     list_deystviy += poisk_tp
                                        #     print('List_deystviy 2 стал следующим: ', list_deystviy)
                                        #     # B = False
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
    # print('Лист действий: ', list_deystviy)
    if list_deystviy != []:   # 3.2.3 - было if posl_tp != ()
        list_minus_deystviy = []
        otmena_minus_deystviya = 0    #переменная, чтобы не происходил ответ, если он уже имеется
        # 13.02.23 - добавляю поиск отрицательных реакций у найденных действий, чтобы снизить возможность повторного
        # не верного ответа
        for list_deystviy1 in list_deystviy:
            # поиск связей с текущим ID (tp) и (t0)
            # print("Лист действий, такой ID передаётся: ", list_deystviy1)
            # приходится ID передавать в кортеже
            list_deystviy1_kortez = (list_deystviy1,)
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
                        # print("Найдена связь с (+) - значит применяется действие: ", list_deystviy1)
                        sbor_deystviya(list_deystviy1)
                        otmena_minus_deystviya = 1
                        break   # прекращение цикла
                    # если связи с (+) нет - то ищем связь с (-)
                    poisk_svyazi_t0_s_minus = tuple(cursor.execute(
                        "SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 2", poisk_svyazi_ID_s_t01))
                    # если связи с (-) нет - то применим это действие, а если есть - то впишем его в список
                    # print("Найдены ли связи с (-): ", poisk_svyazi_t0_s_minus)
                    list_minus_deystviy += poisk_svyazi_t0_s_minus
                if list_minus_deystviy == []:
                    # print("Не найдена связь с (-) - значит применяется действие: ", list_deystviy1)
                    sbor_deystviya(list_deystviy1)
                    otmena_minus_deystviya = 1
                    break
            else:
                sbor_deystviya(list_deystviy1)
                otmena_minus_deystviya = 1
                break
        # если цикл дошёл до этой строчки - значит не были найдены (tp) с (+) или без связи с (-) и применяется первая
        # из (tp), связанная с (-)
        # print("otmena_minus_deystviya == ", otmena_minus_deystviya)
        if otmena_minus_deystviya != 1:
            if list_minus_deystviy != []:
                for list_minus_deystviy1 in list_minus_deystviy[0]:
                    # print("Найдена связь с (-) и других действий нет - значит применяется действие: ",
                    #       list_minus_deystviy1)
                    sbor_deystviya(list_minus_deystviy1)
        pogasit_vse_tochki()




def sbor_deystviya(tp):
    # собирает в обратном порядке сущность от последнего tp и приводит в действие ответ
    # print("Разбирается следующий tp: ", tp)
    global posledniy_t_0
    B = True
    tp_kortez = (tp, )
    # 3.2.2 - добавляется поиск уже имеющегося t0 и проверяется имеется ли связь с posl_t0
    poisk_svyazi_tp_s_t0 = tuple(cursor.execute("SELECT ID FROM tochki WHERE rod1 = ? AND name = 'time_0' AND rod2 = ?",
                                                (posledniy_t_0, tp)))
    if poisk_svyazi_tp_s_t0 == ():
        # создать t0 и к нему привязать tp
        new_tochka_t0 = sozdat_new_tochky('time_0', 1, 'time', 'zazech_sosedey', 1, 0, 0, posledniy_t_0, tp, 10)
        # print('new_tochka_t0 такая: ', new_tochka_t0)
        # sozdat_svyaz(new_tochka_t0, tp, 1)  # 3.2.2 - убрал обратную связь
        sozdat_svyaz(posledniy_t_0, new_tochka_t0, 1)
        sozdat_svyaz(new_tochka_t0, tp, 1)
        posledniy_t_0 = new_tochka_t0
        print("Posl_to теперь 5 : ", posledniy_t_0)
    else:
        for poisk_svyazi_tp_s_t01 in poisk_svyazi_tp_s_t0:
            for poisk_svyazi_tp_s_t02 in poisk_svyazi_tp_s_t01:
                posledniy_t_0 = poisk_svyazi_tp_s_t02
                print("Posl_to теперь 6 : ", posledniy_t_0)
                cursor.execute("UPDATE tochki SET work = 1 WHERE ID = ?", (posledniy_t_0,))
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
    # print("Этот же лист, но уже перевернут: ", list_deystviy)
    list_p = []
    for list_deystviy1 in list_deystviy:
        # print('list_deystviy1: ', list_deystviy1)
        otvet_kortez = (list_deystviy1,)
        # print('otvet_kortez: ', otvet_kortez)
        # ищутся сами (р) для формирования ответа
        poisk_svyazi_s_p = tuple(cursor.execute("SELECT id_finish FROM svyazi WHERE id_start = ?", otvet_kortez))
        # print('poisk_svyazi_s_p: ', poisk_svyazi_s_p)
        for poisk_svyazi_s_p1 in poisk_svyazi_s_p:
            poisk_p = tuple(cursor.execute("SELECT name FROM tochki WHERE ID = ? AND type = 'print'",
                                                         poisk_svyazi_s_p1))
            for poisk_p1 in poisk_p:
                for poisk_p2 in poisk_p1:
                    list_p += poisk_p2
    # print('list_p = ', list_p)
    if list_p != []:
        print("Ответ программы: ")
        out_red(list_p)
        # print("\033[31m".join(list_p))
        # print("\033[0m {}".format(""))
        print("")


def sozdat_svyaz_s_4 ():
    # функция берёт posl_tp и соединяет с (4), если такой связи нет - тем самым создавая сущность
    global posledniy_tp
    posledniy_tp_kortez = (posledniy_tp, )
    poisk_svyazi_s_4 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 4",
                                   posledniy_tp_kortez))
    if poisk_svyazi_s_4 == ():
        # если такой связи нет - создать
        sozdat_svyaz(posledniy_tp, 4, 1)



def ymenshenie_signal ():
    # функция находит все (.), где сигнал более 0 и уменьшает на 0,1
    cursor.execute("UPDATE tochki SET signal = signal - 0.1 WHERE signal >= 0.1 AND signal < 1")
    cursor.execute("UPDATE tochki SET signal = signal - 0.01 WHERE signal >= 0 AND signal < 0.1")  #3.2.4 - added


schetchik = 0

while A:
    if rec.status:
        # Блокируем основную программу, пока идет запись
        sleep(0.001)
        continue

    schetchik += 1
    print("schetchik = ", schetchik)
    posledniy_t_0_kortez = (posledniy_t_0,)
    proverka_signal_porog()   # проверка и зажигание точек, если signal >= porog
    concentrator_deystviy()
    print("")
    vvedeno_luboe = input("Введите текст: ")
    print("")
    # print('ввели: ', vvedeno_luboe)
    if vvedeno_luboe == ('0'):
        A = False

    if vvedeno_luboe == ('3'):
        # Включение записи
        sleep(1)
        rec.start()
        continue

    if vvedeno_luboe == ('4'):
        # Показать запись
        sleep(1)
        for i in rec.record:
            print(i)
            play.play_one(i)

    elif vvedeno_luboe == ('9'):
        stiranie_pamyati()
    elif vvedeno_luboe == ('2'):
        # нужно проверить имеется ли уже связь м/у t0 и tp
        # print("Состояние перед (-) реакцией было такое: ", posledniy_t_0, "    С ней и создаётся связь")
        poisk_svyazi_t0_s_2 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 2",
                                                   posledniy_t_0_kortez))
        if poisk_svyazi_t0_s_2 == ():
            sozdat_svyaz(posledniy_t_0, 2, 1)
        pogasit_vse_tochki()
    elif vvedeno_luboe == ('1'):
        # нужно проверить имеется ли уже связь м/у t0 и tp
        print("Состояние перед (+) реакцией было такое: ", posledniy_t_0, "    С ней и создаётся связь")
        poisk_svyazi_t0_s_2 = tuple(cursor.execute("SELECT ID FROM svyazi WHERE id_start = ? AND id_finish = 1",
                                                   posledniy_t_0_kortez))
        if poisk_svyazi_t0_s_2 == ():
            sozdat_svyaz(posledniy_t_0, 1, 1)
        pogasit_vse_tochki()
    elif vvedeno_luboe != "":
        for vvedeno_luboe1 in vvedeno_luboe:
            poisk_bykvi_iz_vvedeno_v2(vvedeno_luboe1)
        proverka_nalichiya_svyazey_t_t_o()
        functions()
        # 3.2.1 - зафиксировать создание новой сущности, создав связь м/у posl_tp и (4)
        sozdat_svyaz_s_4()
        posledniy_tp = 0
        posledniy_t = 0
        # print("Было введено vvedeno_luboe: ", vvedeno_luboe)
        schetchik = 0
    else:
        if schetchik >= 5:
            # 2.2.2: зажигается in0, которая горит, если нет вх.сигналов
            cursor.execute("UPDATE tochki SET work = 0 WHERE ID = 3")
            functions()
            schetchik = 0
            posledniy_t_0 = 3
            print("Posl_to теперь 4 : ", posledniy_t_0)
            print("-----------------------------------Переход в (3)-------------------------------------")
        else:
            functions()
    ymenshenie_signal()



# -------------------------------------------------------------------------------------------
# обязательно весь текст по работе с базой данных вписывать до этих двух строчек

conn.commit()

conn.close()
