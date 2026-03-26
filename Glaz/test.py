#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы зависимостей
"""

import sys

def test_imports():
    """Проверка импортов зависимостей"""
    try:
        import mss
        print("[OK] MSS library imported successfully")
    except ImportError:
        print("[FAIL] MSS library not found")

    try:
        from PIL import Image
        print("[OK] Pillow library imported successfully")
    except ImportError:
        print("[FAIL] Pillow library not found")

    try:
        import tkinter
        print("[OK] Tkinter imported successfully")
    except ImportError:
        print("[FAIL] Tkinter not found")

def test_monitor_detection():
    """Тест обнаружения мониторов"""
    try:
        import mss
        sct = mss.mss()
        monitors = sct.monitors[1:]  # Пропускаем первый элемент
        print(f"[OK] Найдено мониторов: {len(monitors)}")
        for i, monitor in enumerate(monitors, 1):
            print(f"  Монитор {i}: {monitor['width']}x{monitor['height']} на позиции ({monitor['left']}, {monitor['top']})")
    except Exception as e:
        print(f"[FAIL] Ошибка при обнаружении мониторов: {e}")

if __name__ == "__main__":
    print("Тестирование зависимостей Glaz...")
    print("=" * 40)
    test_imports()
    print()
    test_monitor_detection()
    print()
    print("Тестирование завершено!")