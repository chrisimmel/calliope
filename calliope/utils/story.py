import os
import time
from typing import List, Optional

from calliope.models import FramesRequestParamsModel
from calliope.tables import Story, StoryFrame
from calliope.utils.file import (
    create_sequential_filename,
    decode_b64_to_file,
    get_base_filename,
)
from calliope.utils.google import is_google_cloud_run_environment, put_media_file
from calliope.utils.image import (
    ImageFormat,
    convert_png_to_grayscale16,
    convert_png_to_rgb565,
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
    prep_start = time.time()
    is_google_cloud = is_google_cloud_run_environment()
    output_image_format = ImageFormat.fromMediaFormat(parameters.output_image_format)
    print(
        f"🖼️  Processing {len(frames)} frames, cloud={is_google_cloud}, format={output_image_format}"
    )

    for frame_idx, frame in enumerate(frames):
        frame_start = time.time()
        print(f"🖼️  Processing frame {frame_idx + 1}/{len(frames)}")

        image = frame.image
        if image:
            image_updated = False
            if save:
                # Save the original image.
                db_save_start = time.time()
                await image.save().run()
                print(f"   💾 image.save() took {time.time() - db_save_start:.2f}s")

            if is_google_cloud:
                # Save the original PNG image in case we want to see it later.
                cloud_start = time.time()
                put_media_file(image.url)
                print(f"   ☁️  put_media_file() took {time.time() - cloud_start:.2f}s")

            """
            # image_is_monochrome() is taking over 2 minutes to run on today's
            # Flux-generated images! And Flux doesn't ever seem to generate
            # the all-black images that motivated this check. Disable it.
            mono_start = time.time()
            if image_is_monochrome(image.url):
                print(f"   🎨 monochrome check took {time.time() - mono_start:.2f}s - MONOCHROME, skipping")
                # Skip the image if it has only a single color (usually black).
                # (This doesn't appear to work.)
                frame.image = None
                if save:
                    frame_save_start = time.time()
                    await frame.save().run()
                    print(f"   💾 frame.save() (monochrome) took {time.time() - frame_save_start:.2f}s")
                continue
            else:
                print(f"   🎨 monochrome check took {time.time() - mono_start:.2f}s - OK")
            """

            output_image_width = parameters.output_image_width
            output_image_height = parameters.output_image_height
            base_filename = get_base_filename(image.url)
            resized_image_filename = f"media/{base_filename}.rsz.png"

            resize_start = time.time()
            resized_image = resize_image_if_needed(
                image,
                output_image_width,
                output_image_height,
                resized_image_filename,
            )
            resize_time = time.time() - resize_start
            if resized_image:
                print(f"   🔄 image resize took {resize_time:.2f}s")
                image_updated = True
                image = resized_image
            else:
                print(
                    f"   🔄 image resize check took {resize_time:.2f}s - no resize needed"
                )

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
                    final_save_start = time.time()
                    await image.save().run()
                    await frame.save().run()
                    print(
                        f"   💾 final image+frame save took {time.time() - final_save_start:.2f}s"
                    )
                if is_google_cloud:
                    final_cloud_start = time.time()
                    put_media_file(image.url)
                    print(
                        f"   ☁️  final put_media_file() took {time.time() - final_cloud_start:.2f}s"
                    )

        video = frame.video
        if video:
            if save:
                video_save_start = time.time()
                await video.save().run()
                print(f"   🎬 video.save() took {time.time() - video_save_start:.2f}s")
            if is_google_cloud:
                video_cloud_start = time.time()
                put_media_file(video.url)
                print(
                    f"   ☁️  video put_media_file() took {time.time() - video_cloud_start:.2f}s"
                )

        frame_time = time.time() - frame_start
        print(f"🖼️  Frame {frame_idx + 1} processing took {frame_time:.2f}s")

    total_time = time.time() - prep_start
    print(
        f"🖼️  📦 TOTAL prepare_frame_images took {total_time:.2f}s for {len(frames)} frames"
    )


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
