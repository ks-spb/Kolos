# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import pyautogui

def _grab_roi(step=4, roi_around_cursor=True, radius=300):
    """
    Снимок экрана -> вырезанный цветной ROI (RGB, без децимации) и серый с децимацией.
    Возвращает: (roi_rgb, gray_downsampled)
    """
    pil = pyautogui.screenshot()
    rgb_full = np.array(pil)  # RGB
    h_full, w_full = rgb_full.shape[:2]

    # ROI
    if roi_around_cursor:
        pos = pyautogui.position()
        x, y = int(pos.x), int(pos.y)
        r = max(1, int(radius))
        x1, y1 = max(0, x - r), max(0, y - r)
        x2, y2 = min(w_full, x + r), min(h_full, y + r)
        if x2 <= x1 or y2 <= y1:
            raise RuntimeError(f"Пустой ROI: ({x1},{y1})–({x2},{y2}). Увеличьте radius или проверьте позицию курсора.")
        roi_rgb = rgb_full[y1:y2, x1:x2].copy()
    else:
        roi_rgb = rgb_full

    # Серый + децимация
    gray = cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2GRAY)
    s = max(1, int(step))
    gray_ds = gray[::s, ::s]

    if gray_ds.size == 0:
        raise RuntimeError("Матрица после децимации пустая. Уменьшите step или увеличьте radius.")

    return roi_rgb, gray_ds


def screenshot_to_excel_values(path="scr_values.xlsx", step=4, roi_around_cursor=True, radius=300):
    """
    Сохраняет:
      1) Excel (path): на листе 'img' — только числа яркости (0..255), без заливок.
      2) PNG со снимком исходного цветного ROI до любых преобразований.
    Возвращает: (excel_path, png_path, (h, w)) — размеры матрицы в Excel.
    """
    import pandas as pd

    roi_rgb, gray_ds = _grab_roi(step=step, roi_around_cursor=roi_around_cursor, radius=radius)
    h, w = map(int, gray_ds.shape)

    # 1) Excel без форматирования
    df = pd.DataFrame(gray_ds.astype(int))
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, header=False, sheet_name="img")

    # 2) PNG «как есть» (цветной ROI, без децимации)
    base, _ = os.path.splitext(path)
    png_path = base + ".png"
    # OpenCV ожидает BGR — конвертируем из RGB:
    cv2.imwrite(png_path, cv2.cvtColor(roi_rgb, cv2.COLOR_RGB2BGR))

    return path, png_path, (h, w)


def _grab_gray(step=4, roi_around_cursor=True, radius=300):
    """Скриншот -> серый. Опционально ROI вокруг курсора. Децимация step."""
    pil = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2GRAY)

    if roi_around_cursor:
        pos = pyautogui.position()
        x, y = int(pos.x), int(pos.y)
        h, w = img.shape[:2]
        r = int(max(1, radius))
        x1, y1 = max(0, x - r), max(0, y - r)
        x2, y2 = min(w, x + r), min(h, y + r)
        img = img[y1:y2, x1:x2]

    s = max(1, int(step))
    img = img[::s, ::s]
    return img


def screenshot_to_excel_pixels(path="screenshot_pixels.xlsx", step=4, roi_around_cursor=False, radius=200):
    """
    «Пиксель-арт»: каждая ячейка залита оттенком серого.
    Требует установленного xlsxwriter (быстро). Если его нет — явно сообщаем.
    """
    try:
        import xlsxwriter
    except ImportError as e:
        raise RuntimeError(
            "Для screenshot_to_excel_pixels нужен пакет 'xlsxwriter'. "
            "Установи: pip install xlsxwriter"
        ) from e

    img = _grab_gray(step=step, roi_around_cursor=roi_around_cursor, radius=radius)
    h, w = img.shape

    wb = xlsxwriter.Workbook(path)
    ws = wb.add_worksheet("img")
    ws.set_default_row(9)
    ws.set_column(0, w - 1, 1.0)

    fmts = [wb.add_format({"bg_color": f"#{i:02x}{i:02x}{i:02x}",
                           "font_color": f"#{i:02x}{i:02x}{i:02x}"}) for i in range(256)]

    for r in range(h):
        row = img[r]
        for c in range(w):
            ws.write_blank(r, c, None, fmts[int(row[c])])

    wb.close()
    return path, (h, w)


# --- блок запуска (вместо сам-импорта) ---
if __name__ == "__main__":
    xlsx_path, png_path, size = screenshot_to_excel_values(
        path="scr_values.xlsx",
        step=1,                 # децимация для Excel
        roi_around_cursor=True, # True — область вокруг курсора; False — весь экран
        radius=300              # радиус ROI (пиксели)
    )
    print(f"Сохранено: {xlsx_path}, {png_path}; матрица: {size}")
