#!/usr/bin/env python3
"""
Скрипт для отрисовки геометрии лупы с номерами сегментов (как в loupe.py).
Высокое разрешение, подписи чёрным цветом без наложения на линии и друг на друга.
"""

import math
from PIL import Image, ImageDraw, ImageFont

# Размер лупы в программе (loupe_size)
LOUPE_SIZE = 100
# Масштаб для высокого разрешения
SCALE = 10
SIZE = LOUPE_SIZE * SCALE  # 1000

# Цвета
BACKGROUND = (255, 255, 255)
LINE_COLOR = (80, 80, 80)
LABEL_COLOR = (0, 0, 0)
ARROW_COLOR = (0, 0, 0)
BORDER_COLOR = (200, 0, 0)
BORDER_WIDTH = max(1, 2 * SCALE // 5)
ARROW_HEAD_LEN_DEFAULT = 10  # длина "перьев" стрелки в пикселях экрана
ARROW_HEAD_HALF_DEFAULT = 5  # половина ширины основания стрелки


def scalex(x: float) -> float:
    return SIZE / 2 + x * SCALE


def scaley(y: float) -> float:
    return SIZE / 2 + y * SCALE  # Y как в программе: вниз = положительный


def draw_arrow(draw: ImageDraw.ImageDraw, from_xy: tuple[float, float], to_xy: tuple[float, float],
               color: tuple[int, int, int], head_len: float, head_half: float) -> None:
    """Рисует линию от from_xy к to_xy и стрелку остриём в to_xy."""
    x1, y1 = from_xy
    x2, y2 = to_xy
    dx = x2 - x1
    dy = y2 - y1
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return
    ux = dx / d
    uy = dy / d
    # Линия до острия (чуть не доходя, чтобы остриё лежало на сегменте)
    draw.line([(x1, y1), (x2, y2)], fill=color, width=max(1, 2))
    # Треугольник-наконечник: остриё в (x2, y2), база перпендикулярна линии
    base_cx = x2 - ux * head_len
    base_cy = y2 - uy * head_len
    perp_x = -uy * head_half
    perp_y = ux * head_half
    triangle = [
        (x2, y2),
        (base_cx + perp_x, base_cy + perp_y),
        (base_cx - perp_x, base_cy - perp_y),
    ]
    draw.polygon(triangle, fill=color, outline=color)


def main():
    img = Image.new("RGB", (SIZE, SIZE), BACKGROUND)
    draw = ImageDraw.Draw(img)

    cx = 0.0
    cy = 0.0
    r_small = 6 * math.sqrt(2)
    r_large = 12 * math.sqrt(2)
    r_small_int = int(r_small)
    r_large_int = int(r_large)

    # Шрифт для номеров: крупный для читаемости на большом разрешении
    font_size = max(14, 12 + SCALE)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    half = LOUPE_SIZE // 2  # 50 в координатах лупы
    seg_idx = [0]
    label_positions: list[tuple[float, float, str]] = []  # (x, y, str) в координатах лупы
    segment_targets: list[tuple[float, float]] = []  # точка на сегменте, куда указывает стрелка

    def add_line(x1: float, y1: float, x2: float, y2: float, label_dx: float, label_dy: float):
        draw.line(
            [(scalex(x1), scaley(y1)), (scalex(x2), scaley(y2))],
            fill=LINE_COLOR,
            width=max(1, SCALE // 8),
        )
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        segment_targets.append((mx, my))
        label_positions.append((mx + label_dx, my + label_dy, str(seg_idx[0])))
        seg_idx[0] += 1

    # Рамка
    draw.rectangle(
        [
            (0, 0),
            (SIZE - 1, SIZE - 1),
        ],
        outline=BORDER_COLOR,
        width=BORDER_WIDTH,
    )

    # === Перекрестие: влево (0-4) ===
    add_line(cx, cy, cx - 6, cy, -4, 0)
    add_line(cx - 6, cy, cx - r_small_int, cy, -4, 0)
    add_line(cx - r_small_int, cy, cx - 12, cy, -4, 0)
    add_line(cx - 12, cy, cx - r_large_int, cy, -4, 0)
    add_line(cx - r_large_int, cy, -half, cy, -5, 0)

    # Вправо (5-9)
    add_line(cx, cy, cx + 6, cy, 4, 0)
    add_line(cx + 6, cy, cx + r_small_int, cy, 4, 0)
    add_line(cx + r_small_int, cy, cx + 12, cy, 4, 0)
    add_line(cx + 12, cy, cx + r_large_int, cy, 4, 0)
    add_line(cx + r_large_int, cy, half, cy, 5, 0)

    # Вверх (10-14) — подпись выше линии (отрицательный dy)
    add_line(cx, cy, cx, cy - 6, 0, -4)
    add_line(cx, cy - 6, cx, cy - r_small_int, 0, -4)
    add_line(cx, cy - r_small_int, cx, cy - 12, 0, -4)
    add_line(cx, cy - 12, cx, cy - r_large_int, 0, -4)
    add_line(cx, cy - r_large_int, cx, -half, 0, -5)

    # Вниз (15-19) — подпись ниже линии (положительный dy)
    add_line(cx, cy, cx, cy + 6, 0, 4)
    add_line(cx, cy + 6, cx, cy + r_small_int, 0, 4)
    add_line(cx, cy + r_small_int, cx, cy + 12, 0, 4)
    add_line(cx, cy + 12, cx, cy + r_large_int, 0, 4)
    add_line(cx, cy + r_large_int, cx, half, 0, 5)

    # Квадрат 12x12 (20-27) — подписи снаружи квадрата
    add_line(cx - 6, cy - 6, cx, cy - 6, 0, -4)
    add_line(cx, cy - 6, cx + 6, cy - 6, 0, -4)
    add_line(cx + 6, cy - 6, cx + 6, cy, 4, 0)
    add_line(cx + 6, cy, cx + 6, cy + 6, 4, 0)
    add_line(cx + 6, cy + 6, cx, cy + 6, 0, 4)
    add_line(cx, cy + 6, cx - 6, cy + 6, 0, 4)
    add_line(cx - 6, cy + 6, cx - 6, cy, -4, 0)
    add_line(cx - 6, cy, cx - 6, cy - 6, -4, 0)

    # Квадрат 24x24 (28-35)
    add_line(cx - 12, cy - 12, cx, cy - 12, 0, -5)
    add_line(cx, cy - 12, cx + 12, cy - 12, 0, -5)
    add_line(cx + 12, cy - 12, cx + 12, cy, 5, 0)
    add_line(cx + 12, cy, cx + 12, cy + 12, 5, 0)
    add_line(cx + 12, cy + 12, cx, cy + 12, 0, 5)
    add_line(cx, cy + 12, cx - 12, cy + 12, 0, 5)
    add_line(cx - 12, cy + 12, cx - 12, cy, -5, 0)
    add_line(cx - 12, cy, cx - 12, cy - 12, -5, 0)

    # Ромб (36-39)
    add_line(cx, cy - 12, cx + 12, cy, -3, -3)
    add_line(cx + 12, cy, cx, cy + 12, -3, 3)
    add_line(cx, cy + 12, cx - 12, cy, 3, 3)
    add_line(cx - 12, cy, cx, cy - 12, 3, -3)

    # Дуги малого круга (40-47): середина дуги по углу, подпись снаружи
    for i, (start, end) in enumerate([
        (0, 45), (45, 90), (90, 135), (135, 180),
        (180, 225), (225, 270), (270, 315), (315, 360),
    ]):
        mid_deg = (start + end) / 2
        rad = math.radians(mid_deg)
        ox = r_small * math.cos(rad)
        oy = r_small * math.sin(rad)
        out = 4
        lx = ox + out * math.cos(rad)
        ly = oy + out * math.sin(rad)
        bbox = [scalex(-r_small), scaley(-r_small), scalex(r_small), scaley(r_small)]
        draw.arc(bbox, start=start, end=end, fill=LINE_COLOR, width=max(1, SCALE // 8))
        segment_targets.append((ox, oy))
        label_positions.append((lx, ly, str(seg_idx[0])))
        seg_idx[0] += 1

    # Дуги большого круга (48-55)
    for start, end in [
        (0, 45), (45, 90), (90, 135), (135, 180),
        (180, 225), (225, 270), (270, 315), (315, 360),
    ]:
        mid_deg = (start + end) / 2
        rad = math.radians(mid_deg)
        ox = r_large * math.cos(rad)
        oy = r_large * math.sin(rad)
        out = 5
        lx = ox + out * math.cos(rad)
        ly = oy + out * math.sin(rad)
        bbox = [scalex(-r_large), scaley(-r_large), scalex(r_large), scaley(r_large)]
        draw.arc(bbox, start=start, end=end, fill=LINE_COLOR, width=max(1, SCALE // 8))
        segment_targets.append((ox, oy))
        label_positions.append((lx, ly, str(seg_idx[0])))
        seg_idx[0] += 1

    # Дополнительные смещения для подписей, чтобы не налезали друг на друга
    label_offset_x = [0.0] * len(label_positions)
    label_offset_y = [0.0] * len(label_positions)
    # Сдвигаем подписи у плотных мест (перекрестие у центра, квадраты)
    for i in range(20):
        if i in (0, 5, 10, 15):  # первые сегменты от центра — сдвиг побольше
            if i == 0:
                label_offset_x[i], label_offset_y[i] = -6, -4
            elif i == 5:
                label_offset_x[i], label_offset_y[i] = 6, -4
            elif i == 10:
                label_offset_x[i], label_offset_y[i] = -4, 6
            else:
                label_offset_x[i], label_offset_y[i] = -4, -6
    # Квадраты 20-35: смещение уже задано в add_line, доп. сдвиг не нужен
    # Ромб 36-39 — уже со смещением в add_line
    # Дуги: для малого круга (40-47) сдвигаем чуть дальше по радиусу
    for i in range(40, 48):
        label_offset_x[i] = label_positions[i][0] * 0.15
        label_offset_y[i] = label_positions[i][1] * 0.15
    for i in range(48, 56):
        label_offset_x[i] = label_positions[i][0] * 0.12
        label_offset_y[i] = label_positions[i][1] * 0.12

    # Размер наконечника стрелки пропорционален масштабу
    arr_len = max(ARROW_HEAD_LEN_DEFAULT, SCALE)
    arr_half = max(ARROW_HEAD_HALF_DEFAULT, SCALE // 2)
    # Отрисовка стрелок и подписей (сначала стрелки, потом цифры)
    for i, (lx, ly, text) in enumerate(label_positions):
        lx_final = lx + label_offset_x[i]
        ly_final = ly + label_offset_y[i]
        sx = scalex(lx_final)
        sy = scaley(ly_final)
        tx, ty = segment_targets[i]
        tx_sc = scalex(tx)
        ty_sc = scaley(ty)
        draw_arrow(draw, (sx, sy), (tx_sc, ty_sc), ARROW_COLOR, arr_len, arr_half)
        draw.text((sx, sy), text, fill=LABEL_COLOR, font=font, anchor="mm")

    out_path = "loupe_geometry_labeled.png"
    img.save(out_path, "PNG")
    print(f"Сохранено: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
