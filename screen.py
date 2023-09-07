# Модуль, содержащий класс, для считывания информации о текущем экране из очереди,
# куда она поставляется параллельным процессом детектирующим изменения экрана
# и производя первичную обработку и подготовку данных (screen_monitoring.py).
# Формат данных описан в модуле screen_monitoring.

class Screen:
    """ Класс для хранения информации об элементах текущего экрана """

    def __init__(self, queue_hashes=None):
        """ Получает ссылку на очередь при инициализации или позже """
        self.queue_hashes = queue_hashes
        self.screenshot = None  # Изображение экрана
        self.screenshot_hash = None  # pHash изображения экрана
        self.hashes_elements = {}  # Словарь, где ключ pHash элемента экрана (кнопки, значка...),
        # а значение - список [x, y, w, h]: x, y - координаты элемента на изображении,  w, h - ширина и высота элемента.

    def get_screen(self):
        """ Получает из очереди информацию о текущем экране (обновление данных)
        Вернет True если обновил
        """
        if self.queue_hashes is None:
            return False

        if not self.queue_hashes.empty():
            # Получаем данные из очереди
            tmp = self.queue_hashes.get()
            self.screenshot, self.screenshot_hash = tmp[0]
            self.hashes_elements = tmp[1]
            return True
        else:
            return False

    def list_search(self, x, y):
        """ Ищет в списке элемент по координатам.
         Принимает координаты, возвращает хэш или None, если элемента нет
         """
        self.get_screen()
        # Находим, какому элементу принадлежат координаты места клика
        element = [hash for hash, coord in self.hashes_elements.items()
                   if coord[0] < x < coord[2] and coord[1] < y < coord[3]]
        return element[0] if element else None

    def get_element(self, hash):
        """ Возвращает координаты центра элемента по его хэшу
        или None, если элемента нет """
        self.get_screen()

        element = self.hashes_elements.get(hash)
        if not element:
            print('Элемент не найден при воспроизведении')
            return None

        x = (element[2] - element[0]) // 2
        y = (element[3] - element[1]) // 2
        return element[0] + x, element[1] + y


screen = Screen()  # Создаем объект для хранения информации об элементах текущего экрана