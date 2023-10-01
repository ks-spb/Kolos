"""Модуль для отчетов"""

import os
import numpy as np
import cv2


class ImageReport:
    """Создание отчета в виде изображений.
    Класс управляет несколькими папками для сохранения изображений.
    Перед сохранением своего изображения функция (какой-то из компонентов программы создающей отчет)
    должен установить свою папку, куда сохраняются его изображения.
    При первой записи (после инициализации) в определенную папку она очищается, или создается, если ее нет.
    При инициализации Счетчик изображений устанавливается в 0. Каждое следующее сохраняемое изображение
    увеличивает счетчик на 1. Нумерация сквозная, не зависимо в какую папку сохраняется изображение.
    Объект создается в модуле и далее экспортируется в модуль, которому требуется делать отчет.
    """

    def __init__(self):
        """Инициализация"""
        self.number = 0
        self.old_folder = []  # Проинициализированные папки (очищенные или созданные)
        self.folder = None  # Текущая папка для сохранения изображений

    def set_folder(self, folder):
        """Инициализирует папку для сохранения изображений, если папки нет создает ее,
        если есть, то очищает."""
        self.folder = folder
        if self.folder in self.old_folder:
            return  # Папка уже была проинициализирована
        self.old_folder.append(self.folder)

        # Если папки нет, создаем ее
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        else:
            # Если папка есть, то очищаем ее
            for file in os.listdir(self.folder):
                os.remove(f'{self.folder}/{file}')

    def save(self, *images):
        """Принимает изображение в формате NumPy
        Сохранение массива NumPy в jpg файл,
        с именем последовательного номера"""
        if self.folder is None:
            return
        for image in images:
            if image is None:
                # Присваиваем ему пустое изображение
                image = np.zeros((1, 1, 3), np.uint8)
            self.number += 1
            cv2.imwrite(f'{self.folder}/{self.number}.jpg', image)

    @staticmethod
    def circle_an_object(image, elements):
        """Принимает изображение экрана в формате NumPy и список элементов (форматы как в screen_monitoring.py)
        Создает копию изображения и обводит на нем элементы.
        Возвращает новое изображение в формате NumPy"""
        img = image.copy()
        for element in elements:
            x, y, w, h = element
            cv2.rectangle(img, (x, y), (w, h), (0, 0, 255), 2)
        return img


report = ImageReport()  # Создаем объект отчета
