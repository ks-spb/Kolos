# Исключения
class Error(Exception):
    """Базовый класс для других исключений"""
    pass


class TemplateNotFoundError(Error):
    """Шаблон с таким именем не найден в папке с изображениями элементов"""
    pass


class ElementNotFound(Error):
    """Элемент не найден в заданной области или на всем экране"""
    pass


# class Error(Error):
#     """Базовый класс для других исключений"""
#     pass