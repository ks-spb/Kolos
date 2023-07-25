import cv2
import numpy as np


# Открытие изображение C:\python\Kolos\elements_img\sample.png
image = 'C:\python\Kolos\elements_img\elem_230721_130631.png'
img = cv2.imread(image, 0)
img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)[1] # ensure binary

# Делаем фон черным.
# Строим гистограмму изображения
hist = cv2.calcHist([img], [0], None, [256], [0, 256])
# Определяем значение пикселя, которое соответствует наибольшему пику, это фон
background_color = np.argmax(hist)

if background_color != 0:
    # Инвертируем значения пикселей в изображении, чтобы фон был черным - 0
    img = cv2.bitwise_not(img)

num_labels, labels_im = cv2.connectedComponents(img)
print (img)

# Создаём словарь, в котором будем хранить координаты пикселей, принадлежащих каждой компоненте связности
components = {}
for label in range(1, num_labels):
    # Получаем координаты пикселей, которые принадлежат к текущей компоненте связности
    coords = np.where(labels_im == label)
    # Преобразуем координаты в список кортежей и добавляем в словарь
    components[label] = list(zip(coords[0], coords[1]))

print(components)
