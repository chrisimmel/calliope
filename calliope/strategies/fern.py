import json
import sys
import traceback
from typing import Any, Literal, cast, Dict, List, Optional

import httpx
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from calliope.inference import (
    messages_to_object_inference,
    text_to_text_inference,
    text_to_image_file_inference,
    image_and_text_to_video_file_inference,
)
from calliope.location.location import get_local_situation_text
from calliope.models import (
    FramesRequestParamsModel,
    FullLocationMetadata,
    KeysModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import (
    Image,
    InferenceModel,
    ModelConfig,
    SparrowState,
    Story,
    StrategyConfig,
)
from calliope.utils.file import create_character_filename, create_sequential_filename
from calliope.utils.image import get_image_attributes
from calliope.utils.video import get_video_attributes
from calliope.utils.text import (
    balance_quotes,
    ends_with_punctuation,
    split_into_sentences,
    translate_text,
)


class CharacterModel(BaseModel):
    name: str = Field(description="The character's name.")
    description: str = Field(description="Overall description of the character.")
    goal: str = Field(description="What do they want?")
    hair_color: str = Field(description="Their hair color.")
    gender: str = Field(description="Their estimated biological gender.")
    approximate_age: Literal[
        "child", "young_adult", "adult", "middle_aged", "old_and_wise"
    ] = Field(description="Their approximate age.")
    personality: str = Field(description="Their personality.")
    typical_attire: str = Field(
        description="What kind of clothes do they usually wear?"
    )
    other_attributes: dict[str, str] = Field(
        description="Any other notable attributes of the character not otherwise captured by this schema."
    )


class StoryStateModel(BaseModel):
    genre: str = Field(
        description="The story's genre.",
        examples=["Science Fiction", "Mystery", "Adventure"],
    )
    conceit: str = Field(description="The overall conceit or concept of the story.")
    cast: list[CharacterModel] = Field(description="A list of characters in the story.")
    atmosphere: str = Field(
        description="A description of the story's atmosphere, if pertinent."
    )
    principal_setting: str = Field(description="Where the story mainly takes place.")
    secondary_settings: list[str] = Field(
        description="A list of secondary settings in the story."
    )
    sources_of_conflict: list[str] = Field(
        description="A list of sources of conflict or tension in the story."
    )
    past_story_developments: list[str] = Field(
        description="Any past story developments."
    )
    current_story_development: str = Field(
        description="What is happening now in the story."
    )
    possible_future_story_developments: list[str] = Field(
        description="A list of ideas for future story developments."
    )
    story_summary: str = Field(description="A summary of the story.")
    other_elements: dict[str, str] = Field(
        description="Any other pertinent story elements."
    )


class ExtendStoryResponseModel(BaseModel):
    continuation: str = Field(
        description="The continuation of the story. This is the actual text the reader will read."
    )
    illustration: str = Field(
        description="A detailed description of a visual illustration of this portion of the story. This will be used to generate an image."
    )
    video_scene: str = Field(
        description="A detailed description of a short animated scene that begins from the illustration. It should capture some of the feeling and action in this part of the story. Describe any action, camera movement, or other motion that should happen."
    )
    story_state: StoryStateModel = Field(
        description="The updated story state, including the genre, conceit, cast of characters, atmosphere, settings, sources of conflict, past and current story developments, possible future story developments, and any other elements."
    )


@StoryStrategyRegistry.register()
class FernStrategy(StoryStrategy):
    """
    Multiple modernizations:
    * Take full advantage of rich image analysis.
    * Use gpt-neo as a "chaos and creativity engine".
    * Initialize the story with a conceipt and a cast of characters.
    * Stabilize character names and casting relations to people seen in input images.
    * Optionally generate video.
    """

    strategy_name = "fern"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        image_analysis: Optional[Dict[str, Any]],
        location_metadata: FullLocationMetadata,
        strategy_config: StrategyConfig,
        keys: KeysModel,
        sparrow_state: SparrowState,
        story: Story,
        httpx_client: httpx.AsyncClient,
    ) -> StoryFrameSequenceResponseModel:
        print(f"Begin processing strategy {self.strategy_name}...")
        client_id = parameters.client_id
        output_image_style = parameters.output_image_style or (
            # A default image style:
            "The entire image must be a watercolor on paper. "
            "We should see washes of the watercolor paint and the texture of the paper. "
            "Prefer abstraction and softer colors or grayscale. Avoid photorealism. "
            "No signature. Don't sign the painting."
        )

        generate_video = (
            "true" == parameters.extra_fields.get("generate_video", "false").lower()
        )

        situation = get_local_situation_text(image_analysis, location_metadata)
        debug_data = self._get_default_debug_data(
            parameters, strategy_config, situation
        )
        errors: List[str] = []
        image = None
        video = None

        frame_number = await story.get_num_frames()
        if frame_number == 0:
            await self._init_story(
                parameters=parameters,
                story=story,
                situation=situation,
                errors=errors,
                keys=keys,
                httpx_client=httpx_client,
            )

        # Get some recent text.
        last_text = await story.get_text(-10)
        if not last_text or last_text.isspace():
            last_text = await self.get_seed_prompt(strategy_config)

        last_text = (last_text.strip() + " ") if last_text else ""
        print(f"{last_text=}")

        muse_text = await self._consult_muse(last_text, errors, keys, httpx_client)
        print(f"{muse_text=}")
        muse_text = None

        messages = self._compose_messages(
            parameters,
            story,
            last_text,
            muse_text,
            situation,
            strategy_config,
            debug_data,
        )

        # print(f'Text prompt: "{prompt}"')
        story_continuation: Optional[str] = await self._get_new_story_fragment(
            messages,
            strategy_config,
            keys,
            errors,
            httpx_client,
        )

        image_description = None
        story_state = None
        if story_continuation:
            print(f"{story_continuation=}")
            # continuation_json = load_llm_output_as_json(story_continuation)
            # print(f"{continuation_json=}")
            continuation_text = story_continuation.continuation
            image_description = story_continuation.illustration
            video_description = story_continuation.video_scene
            story_state = story_continuation.story_state

        if not continuation_text or continuation_text.isspace():
            continuation_text = situation + "\n"

        continuation_text = self._adjust_contninuation_text(continuation_text)

        if not image_description:
            image_description = continuation_text
            if (
                strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config
                and strategy_config.text_to_text_model_config.prompt_template
                and strategy_config.text_to_text_model_config.prompt_template.target_language  # noqa: E501
                != "en"
            ):
                # Translate the story to English before
                # sending as an image/video prompt.
                image_description = translate_text("en", image_description)

        if image_description:
            # Generate media for the frame, composing a prompt from the frame's text
            media_prompt = output_image_style + " " + image_description
            print(f'Media prompt: "{media_prompt}"')

            for _ in range(2):
                # Allow a retry.
                try:
                    output_image_filename_png = create_sequential_filename(
                        "media", client_id, "out", "png", story.cuid, frame_number
                    )
                    await text_to_image_file_inference(
                        httpx_client,
                        media_prompt,
                        output_image_filename_png,
                        strategy_config.text_to_image_model_config,
                        keys,
                        parameters.output_image_width,
                        parameters.output_image_height,
                    )
                    output_image_filename = output_image_filename_png
                    print(f"Wrote image to file {output_image_filename}.")
                    image = get_image_attributes(output_image_filename)
                    print(f"Image: {image}.")

                    if generate_video and strategy_config.text_to_video_model_config:
                        # Generate the video using the image and text
                        output_video_filename = create_sequential_filename(
                            "media", client_id, "out", "mp4", story.cuid, frame_number
                        )

                        # Generate the video
                        await image_and_text_to_video_file_inference(
                            httpx_client,
                            output_image_filename,
                            video_description,
                            output_video_filename,
                            strategy_config.text_to_video_model_config,
                            keys,
                        )
                        print(f"Wrote video to file {output_video_filename}.")
                        video = get_video_attributes(output_video_filename)
                        print(f"Video: {video}.")
                    break
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)
                    errors.append(str(e))

        # Append and persist the frame to the story.
        frame = await self._add_frame(
            story,
            image,
            continuation_text,
            frame_number,
            debug_data,
            errors,
            video,  # Pass the video to _add_frame
        )

        if story_state:
            print(f"Updating story state to: {story_state}")
            story.state_props = story_state.model_dump()
            await story.save()

        # Return the new frame.
        return StoryFrameSequenceResponseModel(
            frames=[frame],
            debug_data=debug_data,
            errors=errors,
            append_to_prior_frames=True,
        )

    async def _consult_muse(
        self,
        seed: str,
        errors: List[str],
        keys: KeysModel,
        httpx_client: httpx.AsyncClient,
    ) -> str:
        """
        Gets some chaotic text to use as story inspiration.
        """
        try:
            model = (
                await InferenceModel.objects()
                .where(InferenceModel.slug == "huggingface-gpt-neo-2.7B")
                .first()
                .output(load_json=True)
                .run()
            )
            if model:
                model_config = ModelConfig(
                    slug="chaos-and-creativity",
                    description="",
                    model_parameters={},
                    model=model,
                )
            else:
                raise ValueError("No gpt-neo-2.7B model found.")

            text = await text_to_text_inference(httpx_client, seed, model_config, keys)
            print(f"Raw output: '{text}'")
            text = text[len(seed) :].strip()
            print(f"Abbreviated output: '{text}'")
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))
            text = ""

        text = " ".join(text.split(" "))
        text = text.replace("*", "")
        text = text.replace("_", "")
        text = text.replace("�", "'")
        text = text.strip()
        return text

    async def _init_story(
        self,
        parameters: FramesRequestParamsModel,
        story: Story,
        situation: str,
        errors: List[str],
        keys: KeysModel,
        httpx_client: httpx.AsyncClient,
        # image_analysis: Optional[Dict[str, Any]],
    ) -> Story:
        """
        Initializes the story with its genre, conceit, and initial cast of characters.
        """
        story_seed = await self._consult_muse(situation, errors, keys, httpx_client)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {keys.openai_api_key}",
        }
        messages = [
            {
                "role": "system",
                "content": f"Situation: {situation}",
            },
            {
                "role": "system",
                "content": """
You are a storyteller. You are planning the creation of your next story, which you want to be
thoroughly engaging, such that it holds the reader's interest throughout. In later steps, you
will build the story incrementally, a page at a time. You will find below a Story Seed to use
for inspiration. You can use this seed to help establish characters, mood, setting, genre, or
anything else.

For now, you only need to choose:
* a genre.
* an overall conceit or concept. Write enough about this that you will be able to understand
what the story is about as you write the pages, and maintain some continuity and direction.
* a small cast of initial characters. Keep this short for now because you can add more as
the story continues.
* a principal setting, real or imaginary.
* potentially a few secondary settings, real or imaginary. Keep this list short, as you can
always add more settings later.
* any other elements you think are important to the story. This can include themes, objects,
events, ideas for character or story development, or anything else you think is important.
* sources_of_conflict - any conflict or tension you think the story might have.
* past_story_developments - this will be empty for now (unless there is backstory).
* current_story_development - what will be the initial thing happening in the story.
* possible_future_story_developments - ideas for future story development.

A muse is here to help you by introducing less linear or expected aspects to the story.
You can find their contribution in the <MUSE_TEXT>. If you see lively, imaginative, or
otherwise interesting elements in the <MUSE_TEXT>, find ways to use them as inspiration
for any aspect of your story, characters, setting, etc. where they may fit.

You do not need to write the story itself yet. That will come later, one page at a time.

Any or all of the above may be inspired by the given <SITUATION> (location, season, weather,
observed scene, etc.).""".strip(),
            },
            {
                "role": "system",
                "content": """
Assemble your story scenario into the following JSON structure:
{
    "genre": "<THE STORY GENRE>",
    "conceit": "<WHAT THE STORY IS ABOUT>",
    "cast": [
        {
            "name": "THE NAME OF CHARACTER 1",
            "description": "<OVERALL DESCRIPTION OF CHARACTER 1>",
            "goal": "<WHAT DOES CHARACTER 1 WANT>",
            "hair_color": "<HAIR COLOR OF CHARACTER 1>",
            "gender": "<ESTIMATED BIOLOGICAL GENDER OF CHARACTER 1>",
            "approximate_age": "<ONE OF: 'child', 'young_adult', 'adult', 'middle_aged', 'old_and_wise'>",
            "personality": "<PERSONALITY OF CHARACTER 1>",
            "typical_attire": "<WHAT KIND OF CLOTHES CHARACTER 1 USUALLY WEARS>"
            "other_attributes": {
                <ANYTHING NOTABLE ABOUT CHARACTER 1 THAT ISN'T OTHERWISE CAPTURED BY THIS SCHEMA>
            }
        },
        {
            <SAME FOR CHARACTER 2>
        },
        etc.
    ],

    "atmosphere": "<A DESCRIPTION OF THE STORY'S ATMOSPHERE, IF PERTINENT>",
    "principal_setting": "<WHERE THE STORY MAINLY TAKES PLACE>",
    "secondary_settings": [
         "<ANOTHER STORY LOCATION>",
         etc.
    ],
    "sources_of_conflict": [
        "<ANY CONFLICTS OR TENSIONS IN THE STORY>"
    ],
    "past_story_developments: [
        "<ANY PAST STORY DEVELOPMENTS>"
    ],
    "current_story_development: "<WHAT IS HAPPENING NOW IN THE STORY>",
    "possible_future_story_developments: "<IDEAS FOR FUTURE STORY DEVELOPMENTS>",
    "story_summary": "<SUMMARY OF THE STORY (initially empty)>",
    "other_elements": {
        <ANY OTHER PERTINENT STORY ELEMENTS>
    }
}
            """.strip(),
            },
            {
                "role": "user",
                "content": f"""
<MUSE_TEXT>
{story_seed}
</MUSE_TEXT>
""".strip(),
            },
        ]
        model = "gpt-4o"

        if not keys.openai_api_key:
            raise ValueError(
                "Warning: Missing OpenAI authentication key. Aborting request."
            )
        payload = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
        response = await httpx_client.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )
        # TODO: Use OpenAI SDK?
        response.raise_for_status()

        json_response = response.json()
        json_str = json_response["choices"][0]["message"]["content"]
        json_response = json.loads(json_str)
        print(json.dumps(json_response, indent=2))
        story.state_props = json_response
        await story.save()
        return story

    def _compose_messages(
        self,
        parameters: FramesRequestParamsModel,
        story: Story,
        last_text: Optional[str],
        muse_text: Optional[str],
        situation: str,
        strategy_config: StrategyConfig,
        debug_data: Dict[str, Any],
    ) -> list[ChatCompletionMessageParam]:
        input_text = parameters.input_text

        if not last_text:
            #     last_text_lines = last_text.split("\n")
            #     last_text_lines = last_text_lines[-8:]
            #     last_text = "\n".join(last_text_lines)
            # else:
            # If there is no text from the existing story,
            # fall back to either the input_text parameter
            # or the seed prompt, in that order of preference.
            last_text = input_text or (
                strategy_config.seed_prompt_template
                and strategy_config.seed_prompt_template.text
            )
            debug_data["applied_seed_prompt"] = last_text

        if not last_text:
            last_text = ""

        story_state = (
            json.dumps(story.state_props, indent=2) if story.state_props else ""
        )

        messages = [
            {
                "role": "system",
                "content": f"Situation: {situation}",
            },
            {
                "role": "system",
                "content": """
You are a storyteller.

Given: A story in progress, along with various attributes of its state (cast, setting, genre, etc.),
a "situation" that may include things seen in an input image, current location, date, time, season,
weather, etc...

Your task is to:
1. Continue the story with a few short sentences.
2. Create a description of an illustration of this portion of the story (to be given an Illustrator).
3. Describe a short video scene to illustrate this scene, beginning from the image illustration.
4. Update the story state with any new characters, settings, or other elements you introduce.

In the story, incorporate some things, people, text, season, and atmosphere from the scene, location,
and situation.

Use a literary style that is spare but wistful, maybe sometimes with a surprise bit of surrealism or
poetic reflection. Give the characters names. Don't end the story, because you will come back to
continue it later.

No syrupy or pulp romantic drama. No romance. This is not a love story. Use perfect grammar, except
for maybe slang in dialog.

When connecting to a setting, avoid tourist monuments and cultural clichés. E.g, when in Paris, no
Eiffel Tower, baguettes, or berets. When in New York, no Statue of Liberty or Empire State Building.
In Los Angeles, no Hollywood sign.

Don't repeat things too often. If you just said in the previous page that it's raining or that there
are cobblestone streets. You don't need to say it again now.

Be specific about any and all movement in the video scene, including both character and camera
movement. The scene will be a single take, so don't include any cuts or transitions. The video
scene must begin with the illustration as its first frame, so start from there. Don't call for
music or sound, as the video will be silent. Be detailed, but keep the scene description under
1000 characters.

A muse is here to help you by introducing less linear or expected aspects to the story.
You can find their contribution in the <MUSE_TEXT>. If you see lively, imaginative, or
otherwise interesting elements in the <MUSE_TEXT>, find ways to use them as inspiration
for any aspect of your story, characters, setting, etc. where they may fit. You may even
quote literally from the <MUSE_TEXT>.

Similarly, there may sometimes be overheard <SPOKEN_TEXT> that you can treat either as
something overheard within the story, or possibly as commentary on the story itself.
Use it if you can.

Don't let too much time go by without something new happening, or a change of direction.
You can keep track of possible_future_story_developments in the story state, and move
them to the current_story_development when they are ready (or delete them if they
beceome irrelevant). When a current_story_development is no longer in progress, move
it to past_story_developments.

Avoid letting the cast grow too large. If new characters appear in the situation, input image,
or muse text, consider merging them with existing characters.""".strip(),
            },
            {
                "role": "system",
                "content": f"""
<STORY_STATE>
{story_state}
</STORY_STATE>
""".strip(),
            },
            {
                "role": "system",
                "content": f"""
<SITUATION>
{situation}
</SITUATION>
""".strip(),
            },
            #             {
            #                 "role": "system",
            #                 "content": f"""
            # <MUSE_TEXT>
            # {muse_text}
            # </MUSE_TEXT>
            # """.strip(),
            #             },
            {
                "role": "system",
                "content": f"""
<SPOKEN_TEXT>
{input_text}
</SPOKEN_TEXT>
""".strip(),
            },
            {
                "role": "user",
                "content": f"""
<STORY>
{last_text}
</STORY>
""".strip(),
            },
        ]
        return messages

    async def _get_new_story_fragment(
        self,
        messages: list[ChatCompletionMessageParam],
        strategy_config: StrategyConfig,
        keys: KeysModel,
        errors: List[str],
        httpx_client: httpx.AsyncClient,
    ) -> ExtendStoryResponseModel:
        """
        Gets a new story fragment to be used in building the frame's text.
        """
        result = cast(
            ExtendStoryResponseModel,
            await messages_to_object_inference(
                httpx_client,
                messages,
                strategy_config.text_to_text_model_config,
                keys,
                response_model=ExtendStoryResponseModel,
            ),
        )
        print(f"Raw output: '{result}'")

        """
        # Don't want to see fragments of the prompt in the story.
        prompt_words = ("Scene:", "Text:", "Objects:", "Continuation:")
        for prompt_word in prompt_words:
            if text.find(prompt_word) >= 0:
                msg = (
                    "Rejecting story continuation because it contains a prompt word: "
                    f"'{text}'"
                )
                print(msg)
                errors.append(msg)
                text = ""
        """

        return result

    def _adjust_contninuation_text(self, text: str) -> str:
        if text:
            LIMIT = 1024

            if len(text) > LIMIT:
                text_parts = text.split()
                text = ""
                for part in text_parts:
                    # if ends_with_punctuation(part):
                    #    text += part + "\n"
                    # else:
                    text += part + " "

                    if len(text) > LIMIT:
                        break

            lines = split_into_sentences(text)
            if len(lines) > 3:
                # Discard the last line in order to subvert OpenAI models' desire
                # to put an ending on every episode. Also avoids final
                # sentence fragments caused by token limit cutoff.
                print(f"Discarding last sentence: '{lines[-1]}'")
                lines = lines[0:-1]
                # Adding blank lines between sentences helps break up
                # dense text from especially GPT-4-like models.
                text = "\n\n".join(lines)
                text = balance_quotes(text)
            text = text.strip()
            if not ends_with_punctuation(text):
                text += "."

            text += "\n\n"

        return text

    async def _create_character_image(
        self,
        httpx_client: httpx.AsyncClient,
        client_id: str,
        story: Story,
        strategy_config: StrategyConfig,
        keys: KeysModel,
        character: CharacterModel,
    ) -> Image:
        """
        Creates a reference image based on a character's attributes.
        """

        prompt = f"""Generate a photographic image showing the following character in two different poses.
The face must be clearly visible, as well as the basic overall look, costume, and aspects of the
personality of the character. One pose must show the face from a direct frontal angle. The other must
show a profile. We will use this image as a reference when generating further images
of the character in other situations.

name: {character.name}
description: {character.description}
goal: {character.goal}
hair_color: {character.hair_color}
gender: {character.gender}
approximate_age: {character.approximate_age}
personality: {character.personality}
typical_attire: {character.typical_attire}
other_attributes: {character.other_attributes}
        """

        print(f'Image prompt: "{prompt}"')

        try:
            output_image_filename_png = create_character_filename(
                "media", client_id, story.cuid, create_character_filename, "png"
            )
            await text_to_image_file_inference(
                httpx_client,
                prompt,
                output_image_filename_png,
                strategy_config.text_to_image_model_config,
                keys,
                512,
                512,
            )
            output_image_filename = output_image_filename_png
            print(f"Wrote image to file {output_image_filename}.")
            image = get_image_attributes(output_image_filename)
            print(f"Image: {image}.")
            return image
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            print(f"Error generating character image: {e}")
