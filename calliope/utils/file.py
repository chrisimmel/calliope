import os

from calliope.utils.string import slugify


def get_file_extension(filename) -> str:
    """
    Gets the lowercase extension of a filename, or raises a ValueError if there
    is no extension.
    """
    basename = os.path.basename(filename).rsplit(".", 1)
    if not basename and len(basename) > 1:
        raise ValueError(f"Invalid image filename: {filename}")
    return basename[1].lower()


def compose_filename(directory: str, client_id: str, base_filename: str) -> str:
    return f"{directory}/{slugify(client_id)}-{base_filename}"
