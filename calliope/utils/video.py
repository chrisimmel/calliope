import os
import subprocess
from typing import Optional

from calliope.models.video import VideoFormat
from calliope.tables import Video
from calliope.utils.file import get_file_extension


def guess_video_format_from_filename(filename: str) -> VideoFormat:
    """
    Determine the video format based on file extension.
    """
    extension = get_file_extension(filename)
    if extension in ("mp4", "mpeg4"):
        return VideoFormat.MP4
    elif extension in ("webm"):
        return VideoFormat.WEBM
    elif extension in ("mov", "quicktime", "qt"):
        return VideoFormat.MOV
    else:
        # Default to MP4 if unknown
        return VideoFormat.MP4


def get_video_attributes(video_filename: str) -> Video:
    """
    Gets a Video object from a video filename by extracting metadata.
    Uses ffprobe to get accurate video information.
    """
    # Ensure the file exists
    if not os.path.exists(video_filename):
        raise FileNotFoundError(f"Video file {video_filename} not found")

    format = guess_video_format_from_filename(video_filename)

    # Default values in case ffprobe fails
    width = 1280
    height = 720
    duration_seconds = 5.0
    frame_rate = 24.0

    try:
        # Use ffprobe to get video metadata
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration,r_frame_rate",
                "-of", "csv=p=0",
                video_filename
            ],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the output
        # Format: width,height,r_frame_rate,duration
        # e.g: ['960', '960', '24/1', '5.041667']
        metadata = result.stdout.strip().split(',')
        print(f"Video metadata: {metadata}")
        if len(metadata) >= 4:
            width = int(metadata[0])
            height = int(metadata[1])
            # r_frame_rate is in the format "num/den", e.g. "30000/1001"
            frame_rate_parts = metadata[2].split('/')
            print(f"{frame_rate_parts=}")
            if len(frame_rate_parts) == 2:
                frame_rate = float(frame_rate_parts[0]) / float(frame_rate_parts[1])
            else:
                frame_rate = float(frame_rate_parts[0])
            duration_seconds = float(metadata[3])
    except (subprocess.SubprocessError, ValueError, IndexError) as e:
        # Fall back to default values if ffprobe fails
        print(f"Warning: Failed to get video metadata: {e}")

    return Video(
        width=width,
        height=height,
        format=format.value,
        url=video_filename,
        duration_seconds=duration_seconds,
        frame_rate=frame_rate,
    )
