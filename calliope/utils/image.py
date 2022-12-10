import argparse
from enum import Enum
import os
from typing import Optional

import numpy as np
from PIL import Image

from calliope.models import ImageFormat, ImageModel
from calliope.utils.file import get_file_extension


def guess_image_format_from_filename(filename: str) -> ImageFormat:
    extension = get_file_extension(filename)
    if extension in ("raw", "rgb565"):
        return ImageFormat.RGB565
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


def resize_image_if_needed(
    input_image: ImageModel, output_image_width: int, output_image_height: int
) -> ImageModel:
    if output_image_width and output_image_height:
        img = Image.open(input_image.url)
        if img.width != output_image_width or img.height != output_image_height:
            scaling_factor = min(
                output_image_width / img.width, output_image_height / img.height
            )
            resized_width = int(scaling_factor * img.width)
            resized_height = int(scaling_factor * img.height)
            img = img.resize((resized_width, resized_height))
            img.save(input_image.url)
            return ImageModel(
                width=resized_width,
                height=resized_height,
                format=input_image.format,
                url=input_image.url,
            )
    else:
        return input_image


def get_image_attributes(image_filename: str) -> ImageModel:
    image = Image.open(image_filename)
    format = guess_image_format_from_filename(image_filename)

    return ImageModel(
        width=image.width,
        height=image.height,
        format=format,
        url=image_filename,
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


class Mode(Enum):
    RAW = ".raw"
    PNG = ".png"


def main():
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
