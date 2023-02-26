import base64
import os
import json
from calliope.models.story import StoryModel

import cuid
from pydantic import BaseModel

from calliope.utils.string import slugify


filename_counter = 0


def get_base_filename(filename) -> str:
    """
    Gets the lowercase "base name" of a full filename, that is, the part of the filename
    after the path and just before the extension. Raises a ValueError if there is no
    base filename.
    """
    basename = os.path.basename(filename).rsplit(".", 1)
    if not basename and len(basename) > 1:
        raise ValueError(f"Invalid image filename: {filename}")
    return basename[0]


def get_file_extension(filename) -> str:
    """
    Gets the lowercase extension of a filename, or raises a ValueError if there
    is no extension.
    """
    basename = os.path.basename(filename).rsplit(".", 1)
    if not basename and len(basename) > 1:
        raise ValueError(f"Invalid image filename: {filename}")
    return basename[1].lower()


def get_base_filename_and_extension(filename) -> str:
    """
    Gets the base name and extension together.
    """
    return os.path.basename(filename)


def compose_full_filename(directory: str, client_id: str, filename: str) -> str:
    """
    Composes a full filename (filename with path) from the given directory, for the
    given client, using the given filename.
    """
    return f"{directory}/{slugify(client_id)}-{filename}"


def create_unique_filename(directory: str, client_id: str, extension: str) -> str:
    """
    Creates a unique full filename (filename with path) from the given directory, for the
    given client, using the given extension. The name is unique for the lifetime of the
    system, so can be used to avoid collisions in persistent storage.
    """
    base_filename = cuid.cuid()
    return compose_full_filename(directory, client_id, f"{base_filename}.{extension}")


def create_sequential_filename(
    directory: str, client_id: str, tag: str, extension: str, story: StoryModel
) -> str:
    """
    Creates a sequential full filename (filename with path) from the given directory, for the
    given client, using the given extension. The name is assumed to be associated with the current
    frame of the given story, and contains the story ID and frame number in the filename.
    """
    base_filename = story.cuid
    return compose_full_filename(
        directory, client_id, f"{base_filename}.{len(story.frames)}.{tag}.{extension}"
    )


def load_json_into_pydantic_model(json_filename: str, model: BaseModel) -> BaseModel:
    """
    Takes a JSON file path as a string and a Pydantic model class as arguments, reads
    the JSON file, and loads the data into the model.

    (Written by ChatGPT.)
    """
    with open(json_filename, "r") as f:
        data = json.load(f)
    return model(**data)


def write_pydantic_model_to_json(model: BaseModel, json_filename: str):
    """
    Takes a Pydantic model instance and a filename as arguments, converts the model
    to JSON, and writes it to the given filename.

    (Written by ChatGPT.)
    """
    data = model.dict(exclude_none=True)
    with open(json_filename, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def decode_b64_to_file(data: str, filename: str) -> None:
    """
    Decodes a b64-encoded string and stores to a given file.
    """
    bytes = str.encode(data)
    decoded_bytes = base64.b64decode(bytes)
    with open(filename, "wb") as f:
        f.write(decoded_bytes)
