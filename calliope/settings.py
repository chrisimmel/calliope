import os

CALLIOPE_API_KEY = os.environ.get("CALLIOPE_API_KEY", "xyzzy")

CALLIOPE_BUCKET_NAME = os.environ.get(
    "CALLIOPE_BUCKET_NAME", "artifacts.ardent-course-370411.appspot.com"
)

MEDIA_FOLDER = os.environ.get("MEDIA_FOLDER", "media")
