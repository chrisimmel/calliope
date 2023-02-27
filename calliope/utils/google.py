from dataclasses import dataclass
from datetime import datetime
import os
from typing import Sequence, Tuple

from google.cloud import storage

from calliope.settings import settings
from calliope.utils.file import FileMetadata

GOOGLE_CLOUD_MARKER_VARIABLE = "K_SERVICE"


def is_google_cloud_run_environment() -> bool:
    return bool(os.environ.get(GOOGLE_CLOUD_MARKER_VARIABLE))


def put_media_file(filename: str) -> None:
    put_google_file(settings.MEDIA_FOLDER, filename)


def get_media_file(base_filename: str, destination_path: str) -> FileMetadata:
    return get_google_file(settings.MEDIA_FOLDER, base_filename, destination_path)


def put_google_file(google_folder: str, filename: str) -> None:
    storage_client = storage.Client()
    bucket = storage_client.bucket(settings.CALLIOPE_BUCKET_NAME)

    blob_name = f"{google_folder}/{os.path.basename(filename)}"
    blob = bucket.blob(blob_name)

    blob.upload_from_filename(filename)


def get_google_file(filename: str, destination_path: str) -> FileMetadata:
    storage_client = storage.Client()

    bucket = storage_client.bucket(settings.CALLIOPE_BUCKET_NAME)
    blob = bucket.blob(filename)

    blob.download_to_filename(destination_path)
    return FileMetadata(destination_path, blob.time_created, blob.updated)


def get_google_file_metadata(filename: str) -> FileMetadata:
    storage_client = storage.Client()

    bucket = storage_client.bucket(settings.CALLIOPE_BUCKET_NAME)
    blob = bucket.blob(filename)

    return FileMetadata(filename, blob.time_created, blob.updated)


def delete_google_file(google_folder: str, base_filename: str) -> str:
    storage_client = storage.Client()

    bucket = storage_client.bucket(settings.CALLIOPE_BUCKET_NAME)
    blob_name = f"{google_folder}/{os.path.basename(base_filename)}"
    blob = bucket.blob(blob_name)
    blob.delete()


def list_google_files_with_prefix(prefix, delimiter=None) -> Sequence[str]:
    """
    Lists the filenames (the names of the blobs) in the bucket that begin
    with the prefix.

    This can be used to list all blobs in a "folder", e.g. "public/".

    The delimiter argument can be used to restrict the results to only the
    "files" in the given "folder". Without the delimiter, the entire tree under
    the prefix is returned. For example, given these blobs:

        a/1.txt
        a/b/2.txt

    If you specify prefix ='a/', without a delimiter, you'll get back:

        a/1.txt
        a/b/2.txt

    However, if you specify prefix='a/' and delimiter='/', you'll get back
    only the file directly under 'a/':

        a/1.txt

    As part of the response, you'll also get back a blobs.prefixes entity
    that lists the "subfolders" under `a/`:

        a/b/
    """
    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(
        settings.CALLIOPE_BUCKET_NAME, prefix=prefix, delimiter=delimiter
    )

    # Note: The call returns a response only when the iterator is consumed.
    return [blob.name for blob in blobs]
