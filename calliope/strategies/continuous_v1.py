import re
import sys, traceback
from typing import Any, Dict, List, Optional

import aiohttp

from calliope.inference import (
    caption_to_prompt,
    text_to_extended_text_inference,
    text_to_image_file_inference,
)
from calliope.models import (
    FramesRequestParamsModel,
    KeysModel,
    InferenceModelConfigsModel,
    # StoryFrameSequenceResponseModel,
)
from calliope.models.frame_sequence_response import StoryFrameSequenceResponseModel
from calliope.strategies.base import DEFAULT_MIN_DURATION_SECONDS, StoryStrategy
from calliope.strategies.registry import StoryStrategyRegistry
from calliope.tables import (
    SparrowState,
    Story,
)
from calliope.tables.model_config import StrategyConfig
from calliope.utils.file import create_sequential_filename
from calliope.utils.image import get_image_attributes
from calliope.utils.string import split_into_sentences


SHADOW_STORY = """
To the right, the sky, to the left, the sea.
And before your eyes, the grass and its flowers.
A cloud, the road, follows its vertical way
Parallel to the plumb line of the horizon,
Parallel to the rider.
The horse races towards its imminent fall
And the other climbs interminably.
How simple and strange everything is.
Lying on my left side
I take no interest in the landscape
And I think only of things that are very vague,
Very vague and very pleasant,
Like the tired look you walk around with
Through this beautiful summer afternoon
To the right, to the left,
Here, there,
In the delirium of uselessness.
"""

STORY_PROMPT_DAVINCI = """
Given a scene, an optional text fragment, a list of people and objects, and a story, continue the story with a few short sentences.
Incorporate some of the scene, people, and objects in the story. Use a literary style as seen in the examples, surrealist.

Below are three examples.

----

Example 1
Scene: "a man standing in a hallway"
Text: "Life is a movie"
Objects: "wall, person, indoor, ceiling, building, man, plaster, smile, standing, glasses, door"

Story:
A frightening stillness will mark that day.
And the shadow of streetlights and fire-alarms will exhaust the light.
All things, the quietest and the loudest, will be silent.
The tugboats the locomotives the wind will glide by in silence.

Continuation:
Smiling in silence, a man stands in the hallway.
He touches the wall and looks to the ceiling.
Stillness hovers around him.
He thinks: Life is a movie.

----

Example 2
Scene: "a black cat on a couch"
Text: ""
Objects: "cat, indoor, couch, table"

Story:
A frightening stillness will mark that day.
And the shadow of streetlights and fire-alarms will exhaust the light.
All things, the quietest and the loudest, will be silent.
The tugboats the locomotives the wind will glide by in silence.

Continuation:
When the dust the stones the missing tears form the sun's robe on the huge deserted squares.
We shall finally hear the voice.
A startled cat looks up, leaps from the couch where it was sleeping. 
A ghostly seagull told me this great terrible silence was my love.

----

Example 3
Scene: ""
Text: ""
Objects: ""

Story:
In the night there are of course the seven wonders
of the world and the greatness tragedy and enchantment.
Forests collide with legendary creatures hiding in thickets.
There is you.
In the night there are the walker`s footsteps the murderer`s
the town policeman`s light from the street lamp and the ragman`s lantern
There is you.

Continuation:
In the night trains go past and boats
and the fantasy of countries where it`s daytime. The last breaths
of twilight and the first shivers of dawn.
There is you.
A piano tune, a shout.
A door slams. A clock.
And not only beings and things and physical sounds.
But also me chasing myself or endlessly going beyond me.

----

Now, here is the real one...

Scene: "$scene"
Text: "$text"
Objects: "$objects"

Story: "$poem"

Continuation:
"""

STORY_PROMPT_CURIE = """
In the night there are of course the seven wonders
of the world and the greatness tragedy and enchantment.
Forests collide with legendary creatures hiding in thickets.
There is you.
In the night there are the walker`s footsteps the murderer`s
the town policeman`s light from the street lamp and the ragman`s lantern
There is you.
In the night trains go past and boats
and the fantasy of countries where it`s daytime. The last breaths
of twilight and the first shivers of dawn.
There is you.
A piano tune, a shout.
A door slams. A clock.
And not only beings and things and physical sounds.
But also me chasing myself or endlessly going beyond me.

$scene, $text, $objects

$poem"""

STORY_PROMPT = STORY_PROMPT_CURIE


@StoryStrategyRegistry.register()
class ContinuousStoryV1Strategy(StoryStrategy):
    """
    Tries to keep a story going, carrying context from a previous frame, if any,
    to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
    where each generation blindly adds something new to the story, based only on
    the step immediately precedent.

    Spread our wings and try larger prompts tuned for GPT-3.

    Returns a single frame.
    """

    strategy_name = "continuous-v1"

    async def get_frame_sequence(
        self,
        parameters: FramesRequestParamsModel,
        image_analysis: Optional[Dict[str, Any]],
        strategy_config: Optional[StrategyConfig],
        keys: KeysModel,
        sparrow_state: SparrowState,
        story: Story,
        aiohttp_session: aiohttp.ClientSession,
    ) -> StoryFrameSequenceResponseModel:
        print(f"Begin processing strategy {self.strategy_name}...")
        client_id = parameters.client_id
        output_image_style = (
            parameters.output_image_style or "A watercolor, paper texture."
        )
        debug_data = self._get_default_debug_data(parameters)
        errors = []
        prompt = None
        image = None

        frame_number = await story.get_num_frames()

        if image_analysis:
            image_scene = image_analysis.get("all_captions")
            image_objects = image_analysis.get("all_tags_and_objects")
            image_text = image_analysis.get("text")

            if image_scene:
                image_scene = image_scene[0:1].upper() + image_scene[1:]
        else:
            image_scene = ""
            image_objects = ""
            image_text = ""

        """
        Use input_text parameter only as the story seed, not for each frame.
        if parameters.input_text:
            if image_scene:
                image_scene = f"{image_scene}. {parameters.input_text}"
            else:
                image_scene = parameters.input_text
        """

        # Get some recent text.
        last_text = await story.get_text(-1)
        last_text = (last_text.strip() + " ") if last_text else ""
        print(f"{last_text=}")

        prompt = self._compose_prompt(
            parameters, story, last_text, image_scene, image_text, image_objects
        )

        print(f'Text prompt: "{prompt}"')
        story_continuation = await self._get_new_story_fragment(
            prompt,
            parameters,
            strategy_config,
            keys,
            errors,
            story,
            last_text,
            aiohttp_session,
        )

        if not story_continuation or story_continuation.isspace():
            # Allow one retry.
            prompt += " " + SHADOW_STORY
            story_continuation = await self._get_new_story_fragment(
                prompt,
                parameters,
                strategy_config,
                keys,
                errors,
                story,
                last_text,
                aiohttp_session,
            )

        if not story_continuation or story_continuation.isspace():
            story_continuation = image_scene + "\n"

        if story_continuation:
            prompt_template = output_image_style + " {x}"
            prompt = caption_to_prompt(story_continuation, prompt_template)
            print(f'Image prompt: "{prompt}"')

            try:
                output_image_filename_png = create_sequential_filename(
                    "media", client_id, "out", "png", story.cuid, frame_number
                )
                await text_to_image_file_inference(
                    aiohttp_session,
                    prompt,
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
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                errors.append(str(e))

        frame = await self._add_frame(
            story,
            image,
            story_continuation,
            frame_number,
            debug_data,
            errors,
        )

        return StoryFrameSequenceResponseModel(
            frames=[frame],
            debug_data=debug_data,
            errors=errors,
            append_to_prior_frames=True,
        )

    def _compose_prompt(
        self,
        parameters: FramesRequestParamsModel,
        story: Story,
        last_text: Optional[str],
        scene: str,
        text: str,
        objects: str,
    ) -> str:
        if last_text:
            last_text_lines = last_text.split("\n")
            last_text_lines = last_text_lines[-8:]
            last_text = "\n".join(last_text_lines)
            prompt = STORY_PROMPT
        else:
            last_text = parameters.input_text or SHADOW_STORY
            prompt = STORY_PROMPT

        prompt = prompt.replace("$poem", last_text)
        prompt = prompt.replace("$scene", scene)
        prompt = prompt.replace("$text", text)
        prompt = prompt.replace("$objects", objects)
        return prompt

    async def _get_new_story_fragment(
        self,
        text: str,
        parameters: FramesRequestParamsModel,
        strategy_config: StrategyConfig,
        keys: KeysModel,
        errors: List[str],
        story: Story,
        last_text: Optional[str],
        aiohttp_session: aiohttp.ClientSession,
    ) -> str:
        try:
            text = await text_to_extended_text_inference(
                aiohttp_session, text, strategy_config.text_to_text_model_config, keys
            )
            print(f"Raw output: '{text}'")

            def ends_with_punctuation(str):
                return len(str) and str[-1] in (
                    ".",
                    "!",
                    "?",
                    ":",
                    ",",
                    ";",
                    "-",
                    '"',
                    "'",
                )

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

                """
                lines = split_into_sentences(text)
                if len(lines) > 3:
                    # Discard the last line in order to subvert GPT-3's desire
                    # to put an ending on every episode.
                    print(f"Discarding last sentence: '{lines[-1]}'")
                    lines = lines[0:-1]
                    text = "\n".join(lines)
                """
                text = text.strip()
                if not ends_with_punctuation(text):
                    text += "."

                text += "\n\n"

        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            errors.append(str(e))

        stripped_text = text.strip()
        input_text = parameters.input_text

        if input_text and stripped_text.find(input_text) >= 0:
            msg = f"Rejecting story continuation because it contains the input text: {stripped_text[:100]}[...]"
            print(msg)
            errors.append(msg)
            text = ""
        elif re.search(r"[<>#^#\\{}]|0x|://", text):
            msg = f"Rejecting story continuation because it smells like code: {stripped_text[:100]}[...]"
            print(msg)
            errors.append(msg)
            text = ""
        elif stripped_text and stripped_text in last_text:
            msg = f"Rejecting story continuation because it's already appeared in the story: {stripped_text[:100]}[...]"
            print(msg)
            errors.append(msg)
            text = ""

        prompt_words = ("Scene:", "Text:", "Objects:", "Continuation:")
        for prompt_word in prompt_words:
            if text.find(prompt_word) >= 0:
                msg = f"Rejecting story continuation because it contains a prompt word: '{text}'"
                print(msg)
                errors.append(msg)
                text = ""

        return text
