from PIL import Image
import numpy as np


def rgb565_to_png(
    rbg565_filename: str, width: int, height: int, output_filename: str
) -> str:

    dtype = np.dtype("B")
    try:
        with open(rbg565_filename, "rb") as f:
            dataArray = np.fromfile(f, dtype)
        # print(numpy_data)
    except IOError:
        print("Error While Opening the file!")

    a = [0] * 3
    a = [a] * width
    a = [a] * height
    a = np.array(a, dtype=np.uint8)
    # AlgorÃ­timo montado baseado nesse site:
    # http://www.barth-dev.de/online/rgb565-color-picker/
    for x in range(0, height):
        for y in range(0, width):
            index = y + width * x
            pixel = dataArray[index]
            # invert byte order
            pixel = ((dataArray[index] & 0xFF) << 8) | (dataArray[index] >> 8)
            # separa as cores
            R = pixel & 0b1111100000000000
            G = pixel & 0b0000011111100000
            B = pixel & 0b0000000000011111
            # shift para a posição correta
            a[x, y, 0] = R >> 8
            a[x, y, 1] = G >> 3
            a[x, y, 2] = B << 3

    # Use PIL to create an image from the new array of pixels
    new_image = Image.fromarray(a, "RGB")
    new_image.save(output_filename)
