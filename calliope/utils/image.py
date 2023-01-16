import argparse
from collections import defaultdict
from enum import Enum
import os
from typing import Sequence, Tuple

import numpy as np
from PIL import Image

from calliope.models import ImageFormat, ImageModel
from calliope.utils.file import get_file_extension


def guess_image_format_from_filename(filename: str) -> ImageFormat:
    extension = get_file_extension(filename)
    if extension in ("raw", "rgb565"):
        return ImageFormat.RGB565
    if extension in ("grayscale16"):
        return ImageFormat.GRAYSCALE16
    elif extension in ("jpg", "jpeg"):
        return ImageFormat.JPEG
    elif extension == "png":
        return ImageFormat.PNG
    else:
        raise ValueError(f"Unrecognized image format for {filename}")


def image_format_to_media_type(image_format: ImageFormat) -> str:
    return image_format.value


# For a good discussion of the RGB565 format,
# see: http://www.barth-dev.de/online/rgb565-color-picker/#

# The below conversion code was inspired by https://github.com/CommanderRedYT


def convert_png_to_rgb565(input_filename: str, output_filename: str) -> ImageModel:
    """
    Converts the given PNG file to RGB565/raw format.
    """
    png = Image.open(input_filename)

    input_image_content = png.getdata()
    output_image_content = np.empty(len(input_image_content), np.uint16)
    for i, pixel in enumerate(input_image_content):
        r = (pixel[0] >> 3) & 0x1F
        g = (pixel[1] >> 2) & 0x3F
        b = (pixel[2] >> 3) & 0x1F
        rgb = r << 11 | g << 5 | b
        output_image_content[i] = rgb

    with open(output_filename, "wb") as output_file:
        output_file.write(output_image_content)

    return ImageModel(
        width=png.width,
        height=png.height,
        format=ImageFormat.RGB565,
        url=output_filename,
    )


def convert_rgb565_to_png(
    input_filename: str, output_filename: str, width: int, height: int
) -> ImageModel:
    """
    Converts the given RGB565/raw file to PNG format.
    """
    with open(input_filename, "r") as input_file:
        dataArray = np.fromfile(input_file, np.uint16)

        png = Image.new("RGB", (width, height))

        for i, word in enumerate(np.nditer(dataArray)):
            r = (word >> 11) & 0x1F
            g = (word >> 5) & 0x3F
            b = word & 0x1F
            png.putpixel((i % width, i // width), (r << 3, g << 2, b << 3))

        png.save(output_filename)

        return ImageModel(
            width=width, height=height, format=ImageFormat.PNG, url=output_filename
        )


def convert_png_to_grayscale16(input_filename: str, output_filename: str) -> ImageModel:
    """
    Converts the given PNG file to 'grayscale-16' format.
    There are 2 pixels per byte, 4 bits (black, white, 14 shades of gray) each.
    """

    png = Image.open(input_filename)
    # Convert to grayscale.
    png = png.convert(mode="L")

    input_image_content = png.getdata()
    output_image_content = np.empty(int(len(input_image_content) / 2), np.uint8)
    i = 0
    for y in range(0, png.size[1]):
        byte = 0
        done = True
        for x in range(0, png.size[0]):
            l = png.getpixel((x, y))
            if x % 2 == 0:
                byte = l >> 4
                done = False
            else:
                byte |= l & 0xF0
                output_image_content[i] = byte
                done = True
                i += 1
        if not done:
            output_image_content[i] = byte

    with open(output_filename, "wb") as output_file:
        output_file.write(output_image_content)

    return ImageModel(
        width=png.width,
        height=png.height,
        format=ImageFormat.GRAYSCALE16,
        url=output_filename,
    )


def convert_grayscale16_to_png(
    input_filename: str, output_filename: str, width: int, height: int
) -> ImageModel:
    """
    Converts 'grayscale-16' file to PNG.
    There are 2 pixels per byte, 4 bits (black, white, 14 shades of gray) each.
    """

    with open(input_filename, "r") as input_file:
        dataArray = np.fromfile(input_file, np.uint8)

        png = Image.new("L", (width, height))

        for i, pixel_pair in enumerate(np.nditer(dataArray)):
            p0 = int(pixel_pair & 0xF) << 4
            i *= 2
            xy = (i % width, i // width)
            png.putpixel(xy, p0)

            p1 = int(pixel_pair)
            i += 1
            xy = (i % width, i // width)
            png.putpixel(xy, p1)

        png.save(output_filename)

        return ImageModel(
            width=width, height=height, format=ImageFormat.PNG, url=output_filename
        )


def resize_image_if_needed(
    input_image: ImageModel, output_image_width: int, output_image_height: int
) -> ImageModel:
    """
    Resizes a given image iff necessary given output_image_width and
    output_image_height.
    """
    if output_image_width and output_image_height:
        img = Image.open(input_image.url)
        if img.width != output_image_width or img.height != output_image_height:
            # Fit the image into the bounding box given by (output_image_width,
            # output_image_height)...
            scaling_factor = min(
                output_image_width / img.width, output_image_height / img.height
            )
            resized_width = int(scaling_factor * img.width)
            resized_height = int(scaling_factor * img.height)
            scaled_image_size = (resized_width, resized_height)
            img = img.resize(scaled_image_size)

            output_image_size = (output_image_width, output_image_height)
            if output_image_size != scaled_image_size:
                # If the scaled image doesn't match the requested image size,
                # add black bars to either side of it...
                new_image = Image.new(
                    "RGB", output_image_size
                )  # A blank image, all black.
                box = (
                    (output_image_width - resized_width) // 2,
                    (output_image_height - resized_height) // 2,
                )

                # Paste the scaled image into the middle of the black image.
                new_image.paste(img, box)
                new_image.save(input_image.url)
                resized_width = output_image_width
                resized_height = output_image_height

            return ImageModel(
                width=resized_width,
                height=resized_height,
                format=input_image.format,
                url=input_image.url,
            )

    return input_image


def get_image_attributes(image_filename: str) -> ImageModel:
    """
    Gets an ImageModel from an image filename.
    """
    image = Image.open(image_filename)
    format = guess_image_format_from_filename(image_filename)

    return ImageModel(
        width=image.width,
        height=image.height,
        format=format,
        url=image_filename,
    )


def get_image_colors(image_filename: str) -> Sequence[Tuple[int, int]]:
    """
    Returns a sequence of (count, color) tuples with colors given in the mode of the image (e.g. RGB).
    """
    image = Image.open(image_filename)
    by_color = defaultdict(int)
    for pixel in image.getdata():
        by_color[pixel] += 1
    # return Image.open(image_filename).getcolors()
    return by_color.items()


def image_is_monochrome(image_filename: str) -> bool:
    """
    Returns True iff the given image is of a single solid d
    """
    colors = get_image_colors(image_filename)
    return colors and len(colors) == 0


class Mode(Enum):
    RAW = ".raw"
    PNG = ".png"


def main():
    """
    A little utility test harness for conversion to/from the rgb565 format.
    """
    parser = argparse.ArgumentParser(
        description="Convert a file from one format to another."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        dest="input_file",
        help="Input file to be converted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        dest="output_file",
        help="Output file to be converted.",
    )
    parser.add_argument(
        "--width",
        dest="width",
        help="The image width in pixels.",
    )
    parser.add_argument(
        "--height",
        dest="height",
        help="The image height in pixels.",
    )
    args = parser.parse_args()
    input_filename = args.input_file
    output_filename = args.output_file
    width = int(args.width) if args.width else 0
    height = int(args.height) if args.height else 0

    input_basename = os.path.basename(input_filename).rsplit(".", 1)

    mode = Mode.RAW if (input_basename[1] == "png") else Mode.PNG

    if output_filename is None:
        output_filename = input_basename[0] + mode.value

    output_basename = os.path.basename(output_filename).rsplit(".", 1)

    if len(output_basename) != 2:
        print("Error: Invalid arguments.")
        exit(1)

    if input_basename[1] not in ["png", "raw"]:
        print("Error: Input file must be a .png or .raw file.")
        exit(1)

    if output_basename[1] not in ["png", "raw"]:
        print("Error: Output file must be a .png or .raw file.")
        print(f"Output file: {output_basename}")
        exit(1)

    if input_basename[1] == output_basename[1]:
        print("Error: Input and output file must be different.")
        exit(1)

    if mode == Mode.PNG:
        convert_rgb565_to_png(input_filename, output_filename, width, height)
    else:
        convert_png_to_rgb565(input_filename, output_filename)


if __name__ == "__main__":
    main()
