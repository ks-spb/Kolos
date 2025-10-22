# Программа собирает элементы экрана в фоновом режиме
# Для этого создается новый процесс (программа работает на отдельном ядре процессора)
# При работе программа регистрирует изменения экрана и на каждом новом экране
# производит поиск элементов, после чего записывает их в очередь, удаляя предыдущий экран из нее

# Какая информация записывается в очередь на выход:
# ((screenshot, screenshot_hash), hashes_elements)
# screenshot - изображение экрана в формате NumPy
# screenshot_hash - pHash изображения screenshot
# hashes_elements - словарь, где ключ pHash элемента экрана (кнопки, значка...),
# а значение - список [x, y, w, h]: x, y - верхняя левая точка,  w, h - ширина, высота.

import mss
import mss.tools
import cv2
from threading import Thread
import time
import datetime
import numpy as np
import zlib
import json
import sqlite3

from db import Database


cursor = sqlite3.connect('screen.db')


def screen_monitor(queue_img):
    """ Запускает поток, который делает скриншоты с заданной периодичностью
    и сообщает если экран изменился. """
    sct = mss.mss()
    # monitor = {'top': 0, 'left': 0, 'width': sct.monitors[0]['width'], 'height': sct.monitors[0]['height']}
    monitor = sct.monitors[1]
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
    """При каждом обновлении экрана очищает выходной список и начинает заполнять его снова,
    разбирая полученный скриншот. По окончании данные помещает в очередь.

    В очередь уходит кортеж:
      ((screenshot, str(id_screen)), stable_elements)
    где stable_elements: dict[stable_key -> [x, y, w, h]].
    """
    print('Запуск процесса')

    # 1) Старт фонового потока, который кладёт в queue_img скриншот и его pHash
    thread = Thread(target=screen_monitor, args=(queue_img,))
    thread.start()

    # -------- 2) Состояние трекера стабильных ID (живёт между кадрами) --------
    # stable_key -> (bbox=(x,y,w,h), last_raw_hash)
    prev_tracks = {}

    def _hamming(a_hex: str, b_hex: str) -> int:
        try:
            return (int(a_hex, 16) ^ int(b_hex, 16)).bit_count()
        except Exception:
            return 64

    def _iou(a, b) -> float:
        ax, ay, aw, ah = a; bx, by, bw, bh = b
        x1 = max(ax, bx); y1 = max(ay, by)
        x2 = min(ax + aw, bx + bw); y2 = min(ay + ah, by + bh)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = aw * ah + bw * bh - inter
        return (inter / union) if union else 0.0

    # Пороги сопоставления «это тот же объект»
    HAMM_THR = 8       # допустимая «битовая» разница pHash
    IOU_THR  = 0.30    # достаточное перекрытие прямоугольников

    # Параметры детекции (две полосы «масштабов»)
    # Можно вынести в константы наверх файла и подстраивать под своё рабочее место.
    SCALES = [
        # (low, high, kernel, min_w, min_h, min_area)
        (50, 150, 3, 8,  8,  80),   # мелкие элементы
        (100, 200, 5, 12, 12, 150), # средние элементы
    ]

    while True:
        if not queue_img.empty():
            start_time = time.time()

            # 3) Получен новый скриншот из потока
            screenshot, screenshot_hash = queue_img.get()
            print('\n------------------------------------------------------------------------------')
            print(f'screen_monitoring. Экран изменился {datetime.datetime.now()}')
            print(f'screen_monitoring. ID изображений: {screenshot_hash}')

            # 4) Подготовка изображения — вытягиваем локальный контраст (устойчивее на тёмных темах)
            gray  = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY) if screenshot.shape[2] == 4 \
                    else cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            norm  = clahe.apply(gray)

            # 5) Поиск контуров на двух «масштабах» и сбор сырых элементов (raw pHash -> bbox)
            #    Дедупликация по форме (оставляем более узкий bbox, если сегмент совпал)
            #    Для БД 'screen' по-прежнему используем СЫРОЙ pHash.
            #    Для этого считаем pHash сегмента и кладём как ключ.
            raw_elements = {}            # dict[str raw_hex -> [x, y, w, h]]
            seen_shapes  = {}            # dict[str shape_hex -> (raw_hex, [x,y,w,h])]
            from image_definition import stable_object_hash_from_matrix  # готовая утилита

            for low, high, k, min_w, min_h, min_area in SCALES:
                edges  = cv2.Canny(norm, low, high)
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
                # Важно: берём дерево контуров — не теряем вложенные иконки
                contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if w < min_w or h < min_h or (w * h) < min_area:
                        continue

                    seg = screenshot[y:y+h, x:x+w]

                    # Сырый pHash для БД экранов
                    raw = cv2.img_hash.pHash(seg)
                    raw_hex = np.array(raw).tobytes().hex().lower()

                    # Устойчивый ключ формы для дедупликации по двум «масштабам»
                    segg = cv2.cvtColor(seg, cv2.COLOR_BGRA2GRAY) if seg.shape[2] == 4 \
                           else cv2.cvtColor(seg, cv2.COLOR_BGR2GRAY)
                    binm = cv2.adaptiveThreshold(segg, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                 cv2.THRESH_BINARY, 11, 2)
                    shape_hex = stable_object_hash_from_matrix((binm > 0).astype("uint8"))

                    prev = seen_shapes.get(shape_hex)
                    if prev is None or (w * h) < (prev[1][2] * prev[1][3]):
                        seen_shapes[shape_hex] = (raw_hex, [int(x), int(y), int(w), int(h)])

                # Если за время обработки кадр обновился — прерываем детекцию,
                # начнём разбор следующего кадра (минимизируем лаг).
                if not queue_img.empty():
                    break

            # Срез (shape → raw) превращаем в mapping raw → bbox
            for raw_hex, box in (v for v in seen_shapes.values()):
                if raw_hex not in raw_elements or (box[2]*box[3]) < (raw_elements[raw_hex][2]*raw_elements[raw_hex][3]):
                    raw_elements[raw_hex] = box

            # Если за время обработки прилетел новый кадр — пропустим текущий результат
            if not raw_elements:
                continue

            # 6) Сопоставление с треком и выпуск СТАБИЛЬНЫХ ключей (живут между кадрами)
            taken_prev = set()
            stable_elements = {}  # dict[stable_key -> [x,y,w,h]]

            for cur_raw, cur_box in raw_elements.items():
                best_key, best_cost = None, 1e9
                for prev_key, (prev_box, prev_raw) in prev_tracks.items():
                    if prev_key in taken_prev:
                        continue
                    d_h = _hamming(prev_raw, cur_raw)
                    iou = _iou(prev_box, cur_box)
                    # Комбинированная стоимость (веса можно подстроить)
                    cost = d_h * 1.0 + (1.0 - iou) * 20.0
                    if cost < best_cost:
                        best_cost = cost
                        best_key = prev_key

                # Проверяем пороги сопоставления
                if best_key is not None:
                    d_h = _hamming(prev_tracks[best_key][1], cur_raw)
                    iou = _iou(prev_tracks[best_key][0], cur_box)
                    if d_h <= HAMM_THR and iou >= IOU_THR:
                        # Это тот же объект → сохраняем старый стабильный ключ
                        stable_key = best_key
                        taken_prev.add(best_key)
                    else:
                        # Новый объект → его стабильный ключ = его ПЕРВЫЙ «сырой» pHash
                        stable_key = cur_raw
                else:
                    # Нет подходящего трека → новый объект
                    stable_key = cur_raw

                stable_elements[stable_key] = cur_box

            # Обновляем трек: последний raw и bbox по стабильному ключу
            prev_tracks = {
                k: (
                    stable_elements[k],
                    # если k — текущий сырой pHash, используем его;
                    # иначе находим сырой pHash по совпадающему bbox (обратный поиск)
                    k if k in raw_elements else next((r for r, b in raw_elements.items()
                                                     if b == stable_elements[k]), k)
                )
                for k in stable_elements.keys()
            }

            # 7) Работа с БД экранов — по СЫРЫМ ключам (как и было)
            COUNT_EL = 5
            screens = cursor.execute("SELECT id, list FROM screen").fetchall()
            id_screen = None
            hashes_screen = None
            max_count = 0
            hash_list = list(raw_elements.keys())   # СЫРЫЕ pHash для БД
            hash_set  = set(hash_list)

            for id_scr, screen_json in screens:
                screen_hashes = set(json.loads(screen_json))
                inter = screen_hashes.intersection(hash_set)
                if len(inter) > max_count:
                    max_count = len(inter)
                    id_screen = id_scr
                    hashes_screen = screen_hashes
            if hashes_screen:
                print("Совпало", max_count, "это", int(max_count / (len(hashes_screen) / 100)), "%")

            if hashes_screen and max_count / (len(hashes_screen) / 100) > COUNT_EL:
                new_hashes = hash_set | hashes_screen
                cursor.execute("UPDATE screen SET list = ? WHERE id = ?",
                               (json.dumps(list(new_hashes)), id_screen))
                print('Обновляем запись об экране id', id_screen)
            else:
                cursor.execute("INSERT INTO screen (list) VALUES (?)", (json.dumps(hash_list),))
                id_screen = cursor.execute('SELECT last_insert_rowid()').fetchone()[0]
                print('Создаем новую запись об экране id', id_screen)
            cursor.commit()

            # 8) Отправляем в очередь СТАБИЛЬНЫЕ ключи и последний скриншот
            while not queue_hashes.empty():
                queue_hashes.get()
            queue_hashes.put(((screenshot, str(id_screen)), stable_elements))

            print(f'Время выполнения: {time.time() - start_time + 0.05:.3f} сек.')
            print('------------------------------------------------------------------------------\n')

# --- принудительное обновление кадра после ховера курсора ---
def force_refresh_after_move(queue_img, dwell: float = 0.6):
    """
    Дать UI время отреагировать на наведение (tooltip/hover-эффекты),
    затем снять скриншот и положить его в очередь так же, как это делает screen_monitor().
    process_changes возьмёт кадр и обновит экран/хэши.
    """
    import time
    import numpy as np
    import pyautogui
    import cv2

    # Небольшая пауза, чтобы всплывающие элементы успели появиться
    if dwell and dwell > 0:
        time.sleep(float(dwell))

    # Делаем скриншот в том же формате, что и мониторинг
    img_pil = pyautogui.screenshot()
    frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

    # Хэш «кадра» (как идентификатор снимка; формат совпадает с monitor)
    ph = cv2.img_hash.pHash(frame)
    frame_hash = np.array(ph).tobytes().hex().lower()

    # Кладём в очередь — дальше сработает обычный пайплайн process_changes
    queue_img.put((frame, frame_hash))
    print(f'force_refresh_after_move: добавлен кадр {frame_hash}')

# --- Глобальная ссылка на входную очередь кадров ---
_FORCE_QUEUE_IMG = None

def register_input_queue(q):
    """Регистрирует очередь кадров, созданную в main.py (queue_img)."""
    global _FORCE_QUEUE_IMG
    _FORCE_QUEUE_IMG = q

def force_refresh_after_move(dwell: float = 0.6):
    """
    Пауза, чтобы UI успел отреагировать на наведение (tooltip/hover),
    затем делаем скриншот и кладём его в ту же очередь, что читает process_changes().
    """
    import time
    import numpy as np
    import cv2
    import pyautogui

    if _FORCE_QUEUE_IMG is None:
        print("force_refresh_after_move: очередь не зарегистрирована (нет register_input_queue)")
        return

    if dwell and dwell > 0:
        time.sleep(float(dwell))

    pil = pyautogui.screenshot()
    frame = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    hash_img = cv2.img_hash.pHash(frame)  # формат тот же, что в screen_monitor() :contentReference[oaicite:0]{index=0}

    # оставляем только самый свежий кадр
    try:
        while not _FORCE_QUEUE_IMG.empty():
            _FORCE_QUEUE_IMG.get_nowait()
    except Exception:
        pass

    _FORCE_QUEUE_IMG.put((frame, hash_img))  # формат тот же: (np_img, pHash) :contentReference[oaicite:1]{index=1}
