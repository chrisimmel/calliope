from datetime import datetime
from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns import (
    Timestamptz,
    Varchar,
    Text,
)
from piccolo.table import Table


ID = "2023-04-09T21:22:21:192157"
VERSION = "0.106.0"
DESCRIPTION = "Seeding the PromptTemplate table."


class PromptTemplate(Table):
    """
    A template for a text prompt to be sent to an inference model, with support for template
    variables and control structures in Jinja2 format.
    """

    # A slug naming the prompt template. No spaces or punctuation other than hyphens.
    slug = Varchar(length=80, unique=True, index=True)

    # Description and commentary on the template. What is it for? Which model(s) does it target?
    description = Text()

    # The raw template text, in Jinja2 format.
    text = Text()

    date_created = Timestamptz()
    date_updated = Timestamptz(auto_update=datetime.now)


prompt_template_specs = [
    {
        "slug": "continue-pass-through",
        "description": """
        A prompt that simply passes through its input as the prompt.
        """,
        "text": """
{{ scene }}, {{ text }}, {{ objects }}

{{ poem }}""",
    },
    {
        "slug": "continuous-v1-curie-simple",
        "description": """
            A simple prompt meant to generate a Desnos-seeded chain of story from GPT-3 Curie.
            Curie doesn't seem to respond well to more elaborate prompts with few-shot examples,
            so this skips all that.
            """,
        "text": """
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

{{ scene }}, {{ text }}, {{ objects }}

{{ poem }}""",
    },
    {
        "slug": "continuous-v1-davinci-few-shot-00",
        "description": """
            A more elaborate few-shot prompt meant to get better text from GPT-3 Davinci.
            It does a good job of incorporating observed elements from the image analysis in the text,
            but the prose is sappy. Possibly due to the "poetic, flowery prose", or maybe it doesn't
            know Herman Melville well enough.
            """,
        "text": """
Given a scene, an optional text fragment, a list of objects, and a story, continue the story with four short, imaginative new sentences.
Incorporate some of the scene and objects in the story. Use poetic, flowery prose in the style of Herman Melville.
Nostalgia, solitude. Don't repeat sentences.

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

Scene: "{{ scene }}"
Text: "{{ text }}"
Objects: "{{ objects }}"

Story: "{{ poem }}"

Continuation:
            """,
    },
    {
        "slug": "continuous-v1-gpt-4-few-shot-00",
        "description": """
            Improving from continuous-v1-davinci-few-shot-00, still few-shot. Trying to make prose less
            flowery. Tuning for GPT-4.
            """,
        "text": """
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

Scene: "{{ scene }}"
Text: "{{ text }}"
Objects: "{{ objects }}"

Story: "{{ poem }}"

Continuation:
""",
    },
    {
        "slug": "styled-image",
        "description": """
        The standard prompt for text-to-image models. Combines an output_image_style with the prompt_text.
        """,
        "text": """
{{ output_image_style }} {{ prompt_text }}"
        """,
    },
    {
        "slug": "desnos-seed",
        "description": """
        A parameterless seed for a Desnos-inspired story.
        """,
        "text": """
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
""",
    },
]


async def forwards():
    manager = MigrationManager(migration_id=ID, app_name="", description=DESCRIPTION)

    async def run():
        print(f"running {ID}")
        now = datetime.now()

        for template_spec in prompt_template_specs:
            prompt_template = PromptTemplate(
                slug=template_spec["slug"],
                description=template_spec["description"],
                text=template_spec["text"],
                date_created=now,
                date_updated=now,
            )
            print(f"Saving prompt template {prompt_template}")
            await prompt_template.save().run()

    manager.add_raw(run)

    return manager
