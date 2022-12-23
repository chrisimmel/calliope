import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

from calliope.utils.google import (
    get_media_file,
    is_google_cloud_run_environment,
)
from calliope.utils.image import (
    guess_image_format_from_filename,
    image_format_to_media_type,
)


router = APIRouter(prefix="/v1", tags=["media"])


@router.get("/media/{filename}")
async def get_media(
    filename: str,
    # api_key: APIKey = Depends(get_api_key),
) -> Optional[FileResponse]:
    return await handle_media_request(filename)


async def handle_media_request(filename: str) -> Optional[FileResponse]:
    base_filename = filename
    format = guess_image_format_from_filename(base_filename)
    media_type = image_format_to_media_type(format)

    local_filename = f"media/{base_filename}"
    if is_google_cloud_run_environment():
        try:
            get_media_file(base_filename, local_filename)
        except Exception as e:
            raise HTTPException(
                status_code=404, detail=f"Error retrieving file {local_filename}: {e}"
            )

    if not os.path.isfile(local_filename):
        raise HTTPException(
            status_code=404, detail=f"Media file not found: {local_filename}"
        )

    return FileResponse(local_filename, media_type=media_type)
