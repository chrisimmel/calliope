import os

from google.cloud import storage

from calliope.settings import CALLIOPE_BUCKET_NAME, MEDIA_FOLDER

GOOGLE_CLOUD_MARKER_VARIABLE = "K_SERVICE"


def is_google_cloud_run_environment() -> bool:
    return bool(os.environ.get(GOOGLE_CLOUD_MARKER_VARIABLE))


def stash_media_file(filename: str) -> None:
    storage_client = storage.Client()
    bucket = storage_client.bucket(CALLIOPE_BUCKET_NAME)

    blob_name = f"{MEDIA_FOLDER}/{os.path.basename(filename)}"
    blob = bucket.blob(blob_name)

    blob.upload_from_filename(filename)


def get_media_file(base_filename: str, destination_path: str) -> str:
    storage_client = storage.Client()

    bucket = storage_client.bucket(CALLIOPE_BUCKET_NAME)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob_name = f"{MEDIA_FOLDER}/{os.path.basename(base_filename)}"
    blob = bucket.blob(blob_name)

    blob.download_to_filename(destination_path)
