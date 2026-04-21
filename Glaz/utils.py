"""
Системные утилиты для приложения Glaz
"""

import ctypes
import json
import os
from datetime import datetime


def compute_lines_to_delete(current_lines: int, max_lines: int) -> int:
    """
    Сколько строк нужно удалить из начала, чтобы осталось не больше max_lines.

    Args:
        current_lines: текущее количество строк в буфере
        max_lines: максимальное количество строк

    Returns:
        Количество строк для удаления (>= 0).
    """
    if max_lines <= 0:
        return max(0, int(current_lines))
    return max(0, int(current_lines) - int(max_lines))


def get_cursor_pos() -> tuple[int, int]:
    """
    Получение глобальных координат курсора мыши (Windows).
    
    Returns:
        tuple: (x, y) координаты курсора
    """
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x: int, y: int) -> None:
    """
    Установка глобальных координат курсора мыши (Windows).

    Args:
        x: Горизонтальная координата экрана
        y: Вертикальная координата экрана
    """
    ctypes.windll.user32.SetCursorPos(int(x), int(y))


def get_downloads_path() -> str:
    """
    Получение пути к папке Загрузки.
    
    Returns:
        str: Путь к папке Downloads
    """
    return os.path.join(os.path.expanduser("~"), "Downloads")


def generate_filename(prefix: str, extension: str = "png") -> str:
    """
    Генерация имени файла с временной меткой.

    Args:
        prefix: Префикс имени файла
        extension: Расширение файла

    Returns:
        str: Имя файла вида prefix_YYYYMMDD_HHMMSS.extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def get_objects_db_path() -> str:
    """
    Путь к файлу базы определённых объектов.
    Хранится в папке .glaz в домашней директории пользователя.
    """
    home = os.path.expanduser("~")
    db_dir = os.path.join(home, ".glaz")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "objects.json")


def _signature_diff_pct(signature: tuple[int, ...], existing: tuple[int, ...]) -> float:
    """Доля отличия (0..1): симметричная разность / max размеров."""
    if not signature and not existing:
        return 0.0
    sig_set = set(signature)
    diff_count = len(sig_set.symmetric_difference(existing))
    denom = max(len(signature), len(existing))
    return diff_count / denom if denom else 0.0


def find_similar_signature(
    signature: tuple[int, ...],
    signatures_dict: dict[tuple[int, ...], list[int]],
    max_diff: int = 2
) -> tuple[int, ...] | None:
    """
    Поиск подписи с допуском max_diff отличий (fuzzy matching).
    Отличие = симметричная разность множеств (сегменты есть в одной, но нет в другой).
    
    Args:
        signature: искомая подпись (кортеж индексов сегментов)
        signatures_dict: словарь подписей для поиска
        max_diff: максимальное допустимое количество отличий
        
    Returns:
        Найденная похожая подпись или None
    """
    sig_set = set(signature)
    for existing_sig in signatures_dict:
        diff = len(sig_set.symmetric_difference(existing_sig))
        if diff <= max_diff:
            return existing_sig
    return None


def find_similar_signature_by_pct(
    signature: tuple[int, ...],
    signatures_dict: dict[tuple[int, ...], list[int]],
    max_diff_pct: float = 0.2
) -> tuple[tuple[int, ...], float] | None:
    """
    Поиск подписи по допустимой доле отличия (в пределах max_diff_pct, например 0.2 = 20%).
    Если несколько подписей подходят — возвращается та, у которой отличие минимально.

    Returns:
        (найденная подпись, доля отличия 0..1) или None
    """
    best: tuple[tuple[int, ...], float] | None = None
    for existing_sig in signatures_dict:
        pct = _signature_diff_pct(signature, existing_sig)
        if pct <= max_diff_pct and (best is None or pct < best[1]):
            best = (existing_sig, pct)
    return best


def _parse_signatures_dict(raw: dict) -> tuple[dict[tuple[int, ...], list[int]], list[int]]:
    """
    Вспомогательная функция для парсинга словаря подписей из JSON.
    
    Returns:
        (parsed_dict, all_ids_list)
    """
    result: dict[tuple[int, ...], list[int]] = {}
    all_ids: list[int] = []
    for key, val in raw.items():
        try:
            sig = tuple(int(x) for x in key.split(",") if x.strip() != "")
            if isinstance(val, list):
                ids = [int(x) for x in val]
            else:
                ids = [int(val)]
            result[sig] = ids
            all_ids.extend(ids)
        except (ValueError, AttributeError, TypeError):
            continue
    return result, all_ids


def load_objects_db() -> tuple[
    dict[tuple[int, ...], list[int]],  # full_signatures
    dict[tuple[int, ...], list[int]],  # zoomed_signatures
    int                                 # next_id
]:
    """
    Загрузка базы определённых объектов из файла.
    Поддерживает два типа подписей:
    - full_signatures: полные подписи (шаг 2, лупа 100%)
    - zoomed_signatures: уменьшенные подписи (шаг 1, увеличенная лупа)

    Returns:
        (full_signature_to_ids, zoomed_signature_to_ids, next_refined_id)
    """
    path = get_objects_db_path()
    if not os.path.isfile(path):
        return {}, {}, 1
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}, {}, 1
    
    # Обратная совместимость: старый формат с "signatures"
    if "signatures" in data and "full_signatures" not in data:
        full_raw = data.get("signatures", {})
        zoomed_raw = {}
    else:
        full_raw = data.get("full_signatures", {})
        zoomed_raw = data.get("zoomed_signatures", {})
    
    full_result, full_ids = _parse_signatures_dict(full_raw)
    zoomed_result, zoomed_ids = _parse_signatures_dict(zoomed_raw)
    
    all_ids = full_ids + zoomed_ids
    next_id = max(all_ids) + 1 if all_ids else data.get("next_id", 1)
    
    return full_result, zoomed_result, next_id


def save_objects_db(
    full_signature_to_ids: dict[tuple[int, ...], list[int]],
    zoomed_signature_to_ids: dict[tuple[int, ...], list[int]],
    next_refined_id: int
) -> None:
    """
    Сохранение базы определённых объектов в файл.
    
    Args:
        full_signature_to_ids: словарь полных подписей (лупа 100%)
        zoomed_signature_to_ids: словарь уменьшенных подписей (увеличенная лупа)
        next_refined_id: следующий ID для нового объекта
    """
    path = get_objects_db_path()
    full_raw = {",".join(map(str, sig)): ids for sig, ids in full_signature_to_ids.items()}
    zoomed_raw = {",".join(map(str, sig)): ids for sig, ids in zoomed_signature_to_ids.items()}
    data = {
        "full_signatures": full_raw,
        "zoomed_signatures": zoomed_raw,
        "next_id": next_refined_id
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
