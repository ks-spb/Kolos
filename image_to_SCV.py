import numpy as np
import cv2

# прочитать изображение
img = cv2.imread('in_memory_to_disk.png')

image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

# преобразовать изображение в формат оттенков серого
img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# apply binary thresholding
# Применение бинарного порога к изображению
ret, thresh = cv2.threshold(img_gray, 100, 255, cv2.THRESH_BINARY)

print(thresh)

np.savetxt ("my_data.csv", thresh, delimiter=" ,", fmt=" %.0f ")