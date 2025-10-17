# --- ВСТАВИТЬ в diagram.py (или новый модуль) ---

import math
import sqlite3
from collections import defaultdict, deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ARROW_SCALE = 1/3

# Конвертация сантиметров в пиксели
def _cm_to_px(cm: float, dpi: int) -> int:
    return int(round(cm * dpi / 2.54))

def _load_font(size_px: int) -> ImageFont.ImageFont:
    # Пытаемся взять вменяемый шрифт, иначе дефолтный
    for name in ["DejaVuSans.ttf", "Arial.ttf"]:
        try:
            return ImageFont.truetype(name, size_px)
        except Exception:
            pass
    return ImageFont.load_default()

def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return w, h

def _draw_circle_with_text(draw: ImageDraw.ImageDraw, center, text, font, padding_px=12):
    cx, cy = center
    tw, th = _text_size(draw, text, font)
    r = max(tw, th) // 2 + padding_px
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="black", width=2)
    draw.text((cx - tw // 2, cy - th // 2), text, fill="black", font=font)
    return r  # возвращаем радиус кружка

def _arrow_head(p_end, angle, head_len_px=18, head_width_px=10):
    # Треугольник-стрелка на конце линии
    ex, ey = p_end
    dx = math.cos(angle)
    dy = math.sin(angle)
    left_angle = angle + math.pi - math.atan2(head_width_px, head_len_px)
    right_angle = angle + math.pi + math.atan2(head_width_px, head_len_px)
    p1 = (ex, ey)
    p2 = (ex + head_len_px * math.cos(left_angle), ey + head_len_px * math.sin(left_angle))
    p3 = (ex + head_len_px * math.cos(right_angle), ey + head_len_px * math.sin(right_angle))
    return [p1, p2, p3]

def _line_points_from_circles(a, ra, b, rb):
    # Концы линии по касанию окружностей
    ax, ay = a
    bx, by = b
    angle = math.atan2(by - ay, bx - ax)
    start = (ax + ra * math.cos(angle), ay + ra * math.sin(angle))
    end   = (bx - rb * math.cos(angle), by - rb * math.sin(angle))
    return start, end, angle




def _measure_radius(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, padding_px: int) -> int:
    tw, th = _text_size(draw, text, font)
    return max(tw, th) // 2 + padding_px

def _unique_undirected_edges(edges_dict):
    # из {(s,f): [ids]} делаем множество неориентированных пар (без петель)
    uniq = set()
    for (s, f) in edges_dict.keys():
        if s == f:
            continue
        a, b = (s, f) if s < f else (f, s)
        uniq.add((a, b))
    return list(uniq)

def relax_positions(positions, radii, edges_dict, width_px, height_px, margin_px, dist_px, dpi, iters: int = 250):
    """
    Простая итеративная раскладка:
      — все пары узлов отталкиваются так, чтобы центры были >= dist_px и >= (ra+rb+gap);
      — связанные пары дополнительно «пружинятся» к длине dist_px;
      — узлы придерживаются внутри полей страницы.
    """
    node_ids = list(positions.keys())
    # целевая дистанция по центрам
    target = dist_px
    # небольшой запас к «радиус + радиус»
    min_gap = _cm_to_px(0.2, dpi)

    # список «пружин» для связанных пар
    springs = _unique_undirected_edges(edges_dict)

    # «скорости» и демпфирование
    vx = {n: 0.0 for n in node_ids}
    vy = {n: 0.0 for n in node_ids}
    damp = 0.6
    k_spring = 0.08  # сила пружины
    step_cap = _cm_to_px(0.4, dpi)  # ограничение шага за итерацию

    for _ in range(iters):
        fx = {n: 0.0 for n in node_ids}
        fy = {n: 0.0 for n in node_ids}

        # 1) отталкивание всех со всеми: добиваемся «не ближе» чем target и чем сумма радиусов
        for i in range(len(node_ids)):
            ni = node_ids[i]
            xi, yi = positions[ni]
            ri = radii[ni]
            for j in range(i + 1, len(node_ids)):
                nj = node_ids[j]
                xj, yj = positions[nj]
                rj = radii[nj]

                dx, dy = xj - xi, yj - yi
                d2 = dx * dx + dy * dy
                d = math.sqrt(d2) if d2 > 1e-9 else 1e-4

                desired = max(target, ri + rj + min_gap)
                if d < desired:
                    # толкаем пополам в разные стороны
                    push = (desired - d) * 0.5
                    ux, uy = dx / d, dy / d
                    fx[ni] -= ux * push
                    fy[ni] -= uy * push
                    fx[nj] += ux * push
                    fy[nj] += uy * push

        # 2) пружины на связанных парах: стремимся к target
        for a, b in springs:
            xa, ya = positions[a]
            xb, yb = positions[b]
            dx, dy = xb - xa, yb - ya
            d = math.hypot(dx, dy) or 1e-4
            diff = d - target
            ux, uy = dx / d, dy / d
            fx[a] += ux * diff * k_spring
            fy[a] += uy * diff * k_spring
            fx[b] -= ux * diff * k_spring
            fy[b] -= uy * diff * k_spring

        # 3) мягкие «стены» по полям страницы
        for n in node_ids:
            x, y = positions[n]
            r = radii[n]
            left   = margin_px + r
            right  = width_px - margin_px - r
            top    = margin_px + r
            bottom = height_px - margin_px - r

            if x < left:
                fx[n] += (left - x) * 0.2
            if x > right:
                fx[n] -= (x - right) * 0.2
            if y < top:
                fy[n] += (top - y) * 0.2
            if y > bottom:
                fy[n] -= (y - bottom) * 0.2

        # 4) интегрируем с демпфированием и ограничением шага
        moved_max = 0.0
        for n in node_ids:
            vx[n] = (vx[n] + fx[n]) * damp
            vy[n] = (vy[n] + fy[n]) * damp
            # лимит шага
            sp = math.hypot(vx[n], vy[n])
            if sp > step_cap:
                k = step_cap / sp
                vx[n] *= k
                vy[n] *= k

            x, y = positions[n]
            nx = int(round(x + vx[n]))
            ny = int(round(y + vy[n]))
            positions[n] = (nx, ny)
            moved_max = max(moved_max, math.hypot(vx[n], vy[n]))

        # ранний выход — когда система «у

def draw_graph_from_db(
    db_path: str = "Li_db_v1_4.db",
    out_path: str = "diagram_output.png",
    dpi: int = 300,
    distance_cm: float = 5.0,       # целевая длина ребра (центр-центр)
    arrow_scale: float = 1/3,       # наконечник стрелки уменьшен в 3 раза
    relax_iters: int = 300,         # итераций разведения узлов
    nodes_table: str | None = None  # "points" или "tochki" (None = авто)
):
    import math
    import sqlite3
    from collections import defaultdict, deque
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont

    # ---------- утилиты ----------
    def _cm_to_px(cm: float, dpi_: int) -> int:
        return int(round(cm * dpi_ / 2.54))

    def _load_font(size_px: int) -> ImageFont.ImageFont:
        for name in ("DejaVuSans.ttf", "Arial.ttf"):
            try:
                return ImageFont.truetype(name, size_px)
            except Exception:
                pass
        return ImageFont.load_default()

    def _text_size(draw_: ImageDraw.ImageDraw, text: str, font_: ImageFont.ImageFont):
        bbox = draw_.textbbox((0, 0), text, font=font_)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    def _arrow_head(p_end, angle, head_len_px=18, head_width_px=10):
        ex, ey = p_end
        left_angle = angle + math.pi - math.atan2(head_width_px, head_len_px)
        right_angle = angle + math.pi + math.atan2(head_width_px, head_len_px)
        p1 = (ex, ey)
        p2 = (ex + head_len_px * math.cos(left_angle), ey + head_len_px * math.sin(left_angle))
        p3 = (ex + head_len_px * math.cos(right_angle), ey + head_len_px * math.sin(right_angle))
        return [p1, p2, p3]

    def _line_points_from_circles(a, ra, b, rb):
        ax, ay = a
        bx, by = b
        angle = math.atan2(by - ay, bx - ax)
        start = (ax + ra * math.cos(angle), ay + ra * math.sin(angle))
        end   = (bx - rb * math.cos(angle), by - rb * math.sin(angle))
        return start, end, angle

    def _measure_radius(draw_, text_, font_, padding_px_: int) -> int:
        tw, th = _text_size(draw_, text_, font_)
        return max(tw, th) // 2 + padding_px_

    def _unique_undirected_edges(edges_dict):
        uniq = set()
        for (s, f) in edges_dict.keys():
            if s == f:
                continue
            a, b = (s, f) if s < f else (f, s)
            uniq.add((a, b))
        return list(uniq)

    def _draw_self_loop(draw_, center, radius, label, font_, dpi_):
        cx, cy = center
        loop_r = max(int(radius * 1.2), _cm_to_px(0.6, dpi_))
        offset = int(radius * 1.6)
        angles = [math.radians(a) for a in range(200, 341, 5)]
        pts = [(cx + loop_r*math.cos(a), cy - offset + loop_r*math.sin(a)) for a in angles]
        draw_.line(pts, fill="black", width=2)

        end = pts[-1]
        prev = pts[-2]
        ang = math.atan2(end[1]-prev[1], end[0]-prev[0])
        head_len_px  = int(round(_cm_to_px(0.4, dpi_) * arrow_scale))
        head_width_px = int(round(_cm_to_px(0.2, dpi_) * arrow_scale))
        draw_.polygon(_arrow_head(end, ang, head_len_px=head_len_px, head_width_px=head_width_px), fill="black")

        mid = pts[len(pts)//2]
        lw, lh = _text_size(draw_, label, font_)
        draw_.rectangle((mid[0] - lw/2 - 4, mid[1] - lh - 8, mid[0] + lw/2 + 4, mid[1] - 2), fill="white")
        draw_.text((mid[0] - lw/2, mid[1] - lh - 6), label, fill="black", font=font_)

    def relax_positions(positions, radii, edges_dict, width_px, height_px, margin_px, dist_px, dpi_, iters: int):
        node_ids = list(positions.keys())
        target = dist_px
        min_gap = _cm_to_px(0.2, dpi_)
        springs = _unique_undirected_edges(edges_dict)

        vx = {n: 0.0 for n in node_ids}
        vy = {n: 0.0 for n in node_ids}
        damp = 0.6
        k_spring = 0.08
        step_cap = _cm_to_px(0.4, dpi_)

        for _ in range(iters):
            fx = {n: 0.0 for n in node_ids}
            fy = {n: 0.0 for n in node_ids}

            # отталкивание всех со всеми
            for i in range(len(node_ids)):
                ni = node_ids[i]
                xi, yi = positions[ni]
                ri = radii[ni]
                for j in range(i + 1, len(node_ids)):
                    nj = node_ids[j]
                    xj, yj = positions[nj]
                    rj = radii[nj]
                    dx, dy = xj - xi, yj - yi
                    d2 = dx*dx + dy*dy
                    d = math.sqrt(d2) if d2 > 1e-9 else 1e-4
                    desired = max(target, ri + rj + min_gap)
                    if d < desired:
                        push = (desired - d) * 0.5
                        ux, uy = dx/d, dy/d
                        fx[ni] -= ux*push; fy[ni] -= uy*push
                        fx[nj] += ux*push; fy[nj] += uy*push

            # пружины по связям (как неориентированные пары для устойчивости)
            for a, b in springs:
                xa, ya = positions[a]
                xb, yb = positions[b]
                dx, dy = xb - xa, yb - ya
                d = math.hypot(dx, dy) or 1e-4
                diff = d - target
                ux, uy = dx/d, dy/d
                fx[a] += ux*diff*k_spring; fy[a] += uy*diff*k_spring
                fx[b] -= ux*diff*k_spring; fy[b] -= uy*diff*k_spring

            # мягкие стены
            for n in node_ids:
                x, y = positions[n]
                r = radii[n]
                left   = margin_px + r
                right  = width_px - margin_px - r
                top    = margin_px + r
                bottom = height_px - margin_px - r
                if x < left:   fx[n] += (left - x) * 0.2
                if x > right:  fx[n] -= (x - right) * 0.2
                if y < top:    fy[n] += (top - y) * 0.2
                if y > bottom: fy[n] -= (y - bottom) * 0.2

            moved_max = 0.0
            for n in node_ids:
                vx[n] = (vx[n] + fx[n]) * damp
                vy[n] = (vy[n] + fy[n]) * damp
                sp = math.hypot(vx[n], vy[n])
                if sp > step_cap:
                    k = step_cap / sp
                    vx[n] *= k; vy[n] *= k
                x, y = positions[n]
                nx = int(round(x + vx[n])); ny = int(round(y + vy[n]))
                positions[n] = (nx, ny)
                moved_max = max(moved_max, math.hypot(vx[n], vy[n]))
            if moved_max < 0.5:
                break
        return positions

    def _table_has_columns(cur, table, cols):
        try:
            info = cur.execute(f"PRAGMA table_info({table})").fetchall()
        except Exception:
            return False
        have = {row[1] for row in info}
        return all(c in have for c in cols)
    # ---------- /утилиты ----------

    dist_px = _cm_to_px(distance_cm, dpi)

    # --- читаем БД ---
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # выбираем таблицу с узлами
    if nodes_table is None:
        if _table_has_columns(cur, "points", ["id", "name"]):
            node_table = "points"
        else:
            node_table = "tochki"
    else:
        node_table = nodes_table

    points = cur.execute(f"SELECT id, name FROM {node_table} ORDER BY id").fetchall()
    if not points:
        raise RuntimeError(f"Таблица '{node_table}' пуста.")

    id_to_name = {pid: f"{pid}.{name or ''}" for pid, name in points}

    edges_raw = cur.execute("SELECT id, id_start, id_finish FROM svyazi").fetchall()

    # {(start, finish): [svyaz_ids]} — сразу фильтруем пары, у которых обе вершины существуют
    edges = defaultdict(list)
    for eid, s, f in edges_raw:
        if s in id_to_name and f in id_to_name:
            edges[(s, f)].append(eid)

    # если рёбер нет — всё равно отрисуем «россыпь» узлов
    first_id = points[0][0]

    # --- стартовый холст A4 (альбом), поля ---
    width_px, height_px = _cm_to_px(29.7, dpi), _cm_to_px(21.0, dpi)
    margin_px = _cm_to_px(2.0, dpi)

    # --- начальная раскладка (BFS) ---
    positions = {}
    placed = set()
    positions[first_id] = (margin_px + _cm_to_px(3, dpi), height_px // 2)
    placed.add(first_id)

    # для геометрии используем неориентированную смежность
    adj = defaultdict(set)
    for (s, f) in edges.keys():
        adj[s].add(f)
        adj[f].add(s)

    q = deque([first_id])
    used_angles = defaultdict(int)
    angle_step = math.radians(25)

    while q:
        u = q.popleft()
        ux, uy = positions[u]
        for v in adj[u]:
            if v not in placed:
                shift = used_angles[u]
                ang = (shift // 2 + 1) * angle_step * (1 if shift % 2 == 0 else -1)
                used_angles[u] += 1
                vx = int(round(ux + dist_px * math.cos(ang)))
                vy = int(round(uy + dist_px * math.sin(ang)))
                vx = max(margin_px, min(width_px - margin_px, vx))
                vy = max(margin_px, min(height_px - margin_px, vy))
                positions[v] = (vx, vy)
                placed.add(v)
                q.append(v)

    # несвязанные точки — сеткой
    grid_x = margin_px + _cm_to_px(5, dpi)
    grid_y = margin_px + _cm_to_px(3, dpi)
    step_x = _cm_to_px(7, dpi)
    step_y = _cm_to_px(5, dpi)
    gx, gy = grid_x, grid_y
    for pid, _ in points:
        if pid not in positions:
            positions[pid] = (gx, gy)
            gx += step_x
            if gx > width_px - margin_px - step_x:
                gx = grid_x
                gy += step_y

    # --- измеряем радиусы и разводим узлы ---
    tmp_img = Image.new("RGB", (10, 10), "white")
    tmp_draw = ImageDraw.Draw(tmp_img)
    font = _load_font(size_px=_cm_to_px(0.5, dpi))
    padding_px = _cm_to_px(0.2, dpi)

    radii = {pid: _measure_radius(tmp_draw, id_to_name[pid], font, padding_px) for pid in id_to_name}
    positions = relax_positions(
        positions=positions,
        radii=radii,
        edges_dict=edges,
        width_px=width_px,
        height_px=height_px,
        margin_px=margin_px,
        dist_px=dist_px,
        dpi_=dpi,
        iters=relax_iters,
    )

    # --- авторасширение холста, чтобы всё поместилось с полями ---
    min_x = min(positions[i][0] - radii[i] for i in positions)
    max_x = max(positions[i][0] + radii[i] for i in positions)
    min_y = min(positions[i][1] - radii[i] for i in positions)
    max_y = max(positions[i][1] + radii[i] for i in positions)

    req_w = int(math.ceil((max_x - min_x) + 2*margin_px))
    req_h = int(math.ceil((max_y - min_y) + 2*margin_px))

    if req_w > width_px or req_h > height_px:
        width_px = max(width_px, req_w)
        height_px = max(height_px, req_h)

    # сдвигаем все позиции так, чтобы минимумы попали в поле
    shift_x = margin_px - min_x
    shift_y = margin_px - min_y
    for i in positions:
        x, y = positions[i]
        positions[i] = (int(round(x + shift_x)), int(round(y + shift_y)))

    # --- рисуем ---
    img = Image.new("RGB", (width_px, height_px), "white")
    draw = ImageDraw.Draw(img)

    # кружки + подписи
    for pid, text in id_to_name.items():
        cx, cy = positions[pid]
        r = radii[pid]
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="black", width=2)
        tw, th = _text_size(draw, text, font)
        draw.text((cx - tw // 2, cy - th // 2), text, fill="black", font=font)

    # рёбра (ориентированные)
    for (s, f), eids in edges.items():
        label = ",".join(str(x) for x in sorted(eids))
        if s == f:
            _draw_self_loop(draw, positions[s], radii[s], label, font, dpi)
            continue

        a = positions[s]; b = positions[f]
        ra = radii[s];    rb = radii[f]
        start, end, angle = _line_points_from_circles(a, ra, b, rb)

        draw.line((start[0], start[1], end[0], end[1]), fill="black", width=2)

        head_len_px  = int(round(_cm_to_px(0.4, dpi) * arrow_scale))
        head_width_px = int(round(_cm_to_px(0.2, dpi) * arrow_scale))
        draw.polygon(_arrow_head(end, angle, head_len_px=head_len_px, head_width_px=head_width_px), fill="black")

        midx = (start[0] + end[0]) / 2
        midy = (start[1] + end[1]) / 2
        lw, lh = _text_size(draw, label, font)
        draw.rectangle((midx - lw/2 - 4, midy - lh - 8, midx + lw/2 + 4, midy - 2), fill="white")
        draw.text((midx - lw/2, midy - lh - 6), label, fill="black", font=font)

    img.save(out_path, format="PNG")
    print(f"Диаграмма сохранена: {Path(out_path).resolve()}")


def _draw_self_loop(draw, center, radius, label, font, dpi):
    cx, cy = center
    loop_r = max(int(radius * 1.2), _cm_to_px(0.6, dpi))   # радиус петли
    offset = int(radius * 1.6)                              # поднять петлю над кругом

    # дискретная дуга (ImageDraw.arc без толщины не так красив)
    angles = [math.radians(a) for a in range(200, 341, 5)]  # дуга слева-вверх-вправо
    pts = [(cx + loop_r*math.cos(a), cy - offset + loop_r*math.sin(a)) for a in angles]
    draw.line(pts, fill="black", width=2)

    # наконечник в конце дуги
    end = pts[-1]
    prev = pts[-2]
    angle = math.atan2(end[1]-prev[1], end[0]-prev[0])
    head_len_px  = int(round(_cm_to_px(0.4, dpi) * ARROW_SCALE))
    head_width_px = int(round(_cm_to_px(0.2, dpi) * ARROW_SCALE))
    arrow = _arrow_head(end, angle, head_len_px=head_len_px, head_width_px=head_width_px)
    draw.polygon(arrow, fill="black")

    # подпись ID связи над серединой петли
    mid = pts[len(pts)//2]
    lw, lh = _text_size(draw, label, font)
    draw.rectangle((mid[0] - lw/2 - 4, mid[1] - lh - 8, mid[0] + lw/2 + 4, mid[1] - 2), fill="white")
    draw.text((mid[0] - lw/2, mid[1] - lh - 6), label, fill="black", font=font)

# --- автозапуск при прямом запуске скрипта ---
if __name__ == "__main__":
    from pathlib import Path
    import os, subprocess, platform

    here = Path(__file__).parent

    # Ищем БД рядом со скриптом (оба варианта имени)
    candidates = [
        here / "Li_db_v1_4.db",
        here / "Li_db_v1.4.db",
    ]
    db_path = next((str(c) for c in candidates if c.exists()), str(candidates[0]))

    out_path = str(here / "diagram_output.png")

    # ВЫЗЫВАЕМ «настоящую» функцию (которая сверху файла)
    draw_graph_from_db(
        db_path=db_path,
        out_path=out_path,
        dpi=300,
        distance_cm=5.0,   # можно менять здесь параметром
    )

    # Пробуем открыть готовый файл системной программой
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(out_path)             # noqa: E702
        elif system == "Darwin":
            subprocess.call(["open", out_path])
        else:
            subprocess.call(["xdg-open", out_path])
    except Exception as e:
        print(f"Не удалось открыть файл автоматически: {e}")
