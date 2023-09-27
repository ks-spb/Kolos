"""Модуль для отчетов"""

import os
import numpy as np
import cv2


class ImageReport:
    """Создание отчета в виде изображения.
    Сохраняет переданное изображение в png с именем последовательного номера"""

    def __init__(self):
        """Инициализация"""
        self.number = 0
        # Если папки 'report' нет, то создаем ее
        if not os.path.exists('report'):
            os.mkdir('report')
        else:
            # Если папка есть, то очищаем ее
            for file in os.listdir('report'):
                os.remove(f'report/{file}')

    def save(self, *images):
        """Принимает изображение в формате NumPy
        Сохранение массива NumPy в png файл,
        с именем последовательного номера"""
        for image in images:
            if image is None:
                # Присваиваем ему пустое изображение
                image = np.zeros((1, 1, 3), np.uint8)
            self.number += 1
            cv2.imwrite(f'report/{self.number}.png', image)


