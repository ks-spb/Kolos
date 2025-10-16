# inspect_elements.py
# Запускается отдельно. Показывает:
# 1) какие хэши элементов сейчас на экране;
# 2) какой элемент (ключ из hashes_elements) находится под курсором.
#
# Требования: те же, что у проекта (opencv-python, numpy, pyautogui).
# Управление: 'q' — выход из окна; Ctrl+C — выход из консоли.

import time
import sys
import multiprocessing as mp

import cv2
import numpy as np
import pyautogui

# Берём глобальный экземпляр screen из твоего модуля
from screen import screen  # screen: Screen()

# Настройки
SHOW_WINDOW = True                 # Отрисовывать окно с подсветкой
POLL_DELAY = 0.05                  # Интервал опроса очереди/экрана
MONITOR_FUNC_NAME = "process_changes"  # Имя функции мониторинга в screen_monitoring.py


def start_monitoring(queue):
    """
    Старт фонового процесса мониторинга экрана.
    Ожидается, что в screen_monitoring.py есть функция process_changes(queue),
    которая пишет в очередь кортеж вида: ((screenshot, id_screen), hashes_elements)
    """
    try:
        import screen_monitoring as sm
    except Exception as e:
        print("Не удалось импортировать screen_monitoring.py:", e)
        sys.exit(1)

    fn = getattr(sm, MONITOR_FUNC_NAME, None)
    if fn is None:
        print(f"В screen_monitoring.py нет функции {MONITOR_FUNC_NAME}(...). "
              f"Проверь имя и сигнатуру.")
        sys.exit(1)

    proc = mp.Process(target=fn, args=(queue,), daemon=True)
    proc.start()
    return proc


def draw_overlay(img_bgr, boxes, highlight_key=None, cursor_xy=None):
    """
    Рисуем прямоугольники элементов и подсветку выбранного/под курсором.
    boxes: dict[str -> [x, y, w, h]]
    """
    if img_bgr is None:
        return None

    out = img_bgr.copy()

    # Рамки всех элементов (зелёные)
    for k, (x, y, w, h) in boxes.items():
        color = (0, 255, 0)
        thickness = 1
        if highlight_key is not None and str(k).lower() == str(highlight_key).lower():
            color = (0, 0, 255)   # Красная рамка для элемента под курсором
            thickness = 2
        cv2.rectangle(out, (int(x), int(y)), (int(x + w), int(y + h)), color, thickness)

    # Маркер текущего курсора (синий кружок)
    if cursor_xy is not None:
        cv2.circle(out, (int(cursor_xy[0]), int(cursor_xy[1])), 6, (255, 0, 0), -1)

    return out


def main():
    # На Windows обязательно spawn
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        pass

    q = mp.Queue(maxsize=1)      # Очередь только со свежим кадром
    screen.queue_hashes = q      # Привязываем очередь к нашему Screen
    proc = start_monitoring(q)   # Старт фонового процесса мониторинга

    print("Мониторинг экрана запущен.")
    print("Подсказка: наведите курсор на интересующий элемент — его ключ появится в консоли, "
          "а рамка станет красной.")
    print("Выход: 'q' в окне или Ctrl+C в консоли.")

    last_under = None
    last_dump_t = 0.0

    try:
        while True:
            # Обновляем снимок и карту элементов (если есть новые данные в очереди)
            screen.get_screen()

            # Текущие ключи и карта элементов
            hashes = screen.get_all_hashes()     # list[str]
            boxes = screen.hashes_elements       # dict[str -> [x,y,w,h]]

            # Где находится курсор и какой элемент считается «под курсором»
            pos = pyautogui.position()
            under = screen.element_under_cursor()  # благодаря твоим правкам — это ключ из hashes_elements

            # Печатаем, когда меняется элемент под курсором
            if under != last_under:
                print(f"[{time.strftime('%H:%M:%S')}] Под курсором: {under} | всего элементов: {len(hashes)}")
                if under and under in boxes:
                    x, y, w, h = boxes[under]
                    print(f"  → bbox: x={x}, y={y}, w={w}, h={h}")
                last_under = under

            # Каждые ~2 секунды — короткая сводка по экрану
            now = time.time()
            if now - last_dump_t > 2.0:
                sample = ", ".join(hashes[:10]) + (" ..." if len(hashes) > 10 else "")
                print(f"Сейчас на экране {len(hashes)} элементов. Примеры ключей: {sample}")
                last_dump_t = now

            # Визуализация
            if SHOW_WINDOW and screen.screenshot is not None:
                frame = draw_overlay(screen.screenshot, boxes, highlight_key=under, cursor_xy=(pos.x, pos.y))
                if frame is not None:
                    cv2.imshow("Koloss — инспектор элементов (нажмите 'q' для выхода)", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            time.sleep(POLL_DELAY)

    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        try:
            proc.terminate()
            proc.join(timeout=0.5)
        except Exception:
            pass


if __name__ == "__main__":
    main()
