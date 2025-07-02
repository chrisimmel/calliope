import os
from typing import List, Optional

from calliope.models import (
    FramesRequestParamsModel,
)
from calliope.tables import Story, StoryFrame
from calliope.utils.file import (
    create_sequential_filename,
    decode_b64_to_file,
    get_base_filename,
)
from calliope.utils.google import (
    is_google_cloud_run_environment,
    put_media_file,
)
from calliope.utils.image import (
    convert_png_to_grayscale16,
    convert_png_to_rgb565,
    image_is_monochrome,
    ImageFormat,
    resize_image_if_needed,
)


async def prepare_input_files(
    request_params: FramesRequestParamsModel, story: Story
) -> FramesRequestParamsModel:
    sparrow_id = request_params.client_id

    # Decode b64-encoded file inputs and store to files.
    if request_params.input_image:
        input_image_filename = create_sequential_filename(
            "input",
            sparrow_id,
            "in",
            "jpg",
            story.cuid,
            0,
        )
        decode_b64_to_file(request_params.input_image, input_image_filename)
        request_params.input_image_filename = input_image_filename

    if request_params.input_audio:
        frame_number = await story.get_num_frames()
        input_audio_filename_webm = create_sequential_filename(
            "input", sparrow_id, "in", "webm", story.cuid, frame_number
        )
        decode_b64_to_file(request_params.input_audio, input_audio_filename_webm)
        input_audio_filename_wav = input_audio_filename_webm + ".wav"
        command = f"/usr/bin/ffmpeg -y -i {input_audio_filename_webm} -vn {input_audio_filename_wav}"

        print(f"Executing '{command}'")
        retval = os.system(command)
        if retval == 0:
            request_params.input_audio_filename = input_audio_filename_wav
        else:
            print(f"Warning: ffmpeg failed with return code {retval}")
            # Whisper claims to understand webm, so let it try.
            request_params.input_audio_filename = input_audio_filename_webm

    return request_params


async def prepare_frame_images(
    parameters: FramesRequestParamsModel,
    frames: List[StoryFrame],
    save: bool = True,
) -> None:
    is_google_cloud = is_google_cloud_run_environment()
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)

    for frame in frames:
        image = frame.image
        if image:
            image_updated = False
            if save:
                # Save the original image.
                await image.save().run()
            if is_google_cloud:
                # Save the original PNG image in case we want to see it later.
                put_media_file(image.url)

            if image_is_monochrome(image.url):
                print(f"Image {image.url} is monochrome. Skipping.")
                # Skip the image if it has only a single color (usually black).
                # (This doesn't appear to work.)
                frame.image = None
                if save:
                    await frame.save().run()
                continue

            output_image_width = parameters.output_image_width
            output_image_height = parameters.output_image_height
            base_filename = get_base_filename(image.url)
            resized_image_filename = f"media/{base_filename}.rsz.png"
            resized_image = resize_image_if_needed(
                image,
                output_image_width,
                output_image_height,
                resized_image_filename,
            )
            if resized_image:
                image_updated = True
                image = resized_image

            if output_image_format == ImageFormat.RGB565:
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.raw"
                image = convert_png_to_rgb565(image.url, output_image_filename_raw)
                image_updated = True
            elif output_image_format == ImageFormat.GRAYSCALE16:
                if is_google_cloud:
                    # Also save the original PNG image in case we want to see it later.
                    put_media_file(image.url)
                base_filename = get_base_filename(image.url)
                output_image_filename_raw = f"media/{base_filename}.grayscale16"
                image = convert_png_to_grayscale16(image.url, output_image_filename_raw)
                image_updated = True

            if image_updated:
                frame.image = image
                if save:
                    await image.save().run()
                    await frame.save().run()
                if is_google_cloud:
                    put_media_file(image.url)
        video = frame.video
        if video:
            if save:
                await video.save().run()
            if is_google_cloud:
                put_media_file(video.url)


def prepare_existing_frame_images(
    frames: List[StoryFrame],
) -> None:
    # Always return images in the original size and format.
    for frame in frames:
        frame.image = frame.source_image


def shorten_title(title: Optional[str], max_length: int = 64) -> str:
    if not title:
        return ""

    lines: List[str] = title.split("\n")
    title = ""
    for line in lines:
        if len(title):
            title += " "
        title += line
        if len(title) > max_length:
            break

    if len(title) > max_length:
        return title[:max_length] + "..."

    return title
