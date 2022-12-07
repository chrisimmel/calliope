import os

from google.cloud import storage

from calliope.settings import MEDIA_BUCKET_NAME

GOOGLE_CLOUD_MARKER_VARIABLE = "FUNCTION_REGION"


def is_google_cloud_run_environment() -> bool:
    return bool(os.environ.get(GOOGLE_CLOUD_MARKER_VARIABLE))


def stash_media_file(filename: str) -> None:
    storage_client = storage.Client()
    bucket = storage_client.bucket(MEDIA_BUCKET_NAME)

    destination_blob_name = os.path.basename(filename)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(filename)


def get_media_file(base_filename: str, destination_path: str) -> str:
    storage_client = storage.Client()

    bucket = storage_client.bucket(MEDIA_BUCKET_NAME)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(base_filename)
    blob.download_to_filename(destination_path)
