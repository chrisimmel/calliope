import os

CALLIOPE_API_KEY = os.environ.get("CALLIOPE_API_KEY")

MEDIA_BUCKET_NAME = os.environ.get(
    "MEDIA_BUCKET_NAME", "artifacts.ardent-course-370411.appspot.com/media"
)
