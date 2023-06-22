import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException
from fastapi.security.api_key import APIKey
from starlette.responses import FileResponse

from calliope.utils.authentication import get_api_key
from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.image import (
    guess_image_format_from_filename,
    image_format_to_media_type,
)


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/{filename}")
async def get_media(
    filename: str,
    # api_key: APIKey = Depends(get_api_key),
) -> Optional[FileResponse]:
    """
    Gets a media file, such as for display as part of a story frame.
    """
    return await _handle_get_media_request(filename)


async def _handle_get_media_request(filename: str) -> Optional[FileResponse]:
    format = guess_image_format_from_filename(filename)
    media_type = image_format_to_media_type(format)

    local_filename = f"media/{filename}"
    if is_google_cloud_run_environment():
        try:
            get_media_file(local_filename, local_filename)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Error retrieving file {local_filename}: {e}",
            )

    if not os.path.isfile(local_filename):
        raise HTTPException(
            status_code=404, detail=f"Media file not found: {local_filename}"
        )

    return FileResponse(local_filename, media_type=media_type)


@router.put("/{filename}")
async def put_media(
    filename: str,
    media_file: bytes = File(None),
    api_key: APIKey = Depends(get_api_key),
) -> None:
    """
    Puts a media file in place for later use. Typical usage would be to upload
    an image for use by the 'show-this-frame' strategy.
    """
    local_filename = f"media/{filename}"
    try:
        with open(local_filename, "wb") as f:
            f.write(media_file)

        if is_google_cloud_run_environment():
            put_media_file(local_filename)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error storing file {local_filename}: {e}"
        )

    return None
