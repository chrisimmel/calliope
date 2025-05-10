# Stories

Calliope's central purpose is to tell stories. A story is told something like a graphic
novel, as a sequence of pages (known internally as _frames_), where each page consists of an
image or video, usually paired with text.

## Story Strategies

Calliope constructs a story using a story _strategy_. (These are presented to the user as "storytellers" in Clio. We will likely adopt this name internally as well.) A strategy is a program that embodies a way of generating frames of a story. As we experiment with different ways to create stories, we do so by creating new strategies. As such, the list of available
strategies is likely to remain highly dynamic as experimentation continues.

## Current Story Strategies

### fern
The most sophisticated strategy. Creates and maintains a story based on a genre, concept, a cast of characters, settings, sources of conflict, and a series of story developments. Work is underway to add support for maintaining consistent character appearance by initially generating character images, then using these as references when illustrating the story.

Fern is also currently the only strategy capable of generating video.

### lavender
Similar to the "continuous" strategy series, but takes into account situational context from where the viewer is located: geolocation, local time, season, weather, astronomical events, etc.

### narcissus
A distorting mirror. Creates an image directly from the description of the input text.

### tamarisk
An evolution of the continuous-v0 strategy, specifically based on the Lichen variant,
tuned to use EleutherAI/gpt-neo-2.7B as a source of creative but roughly hewn story material,
then applying gpt-4o to tidy up the results.

### literal
Takes the `input_text` as the prompt to generate an image in a single frame. Echoes back
the text. The `input_text` can be divided into multiple prompts using the `|` character,
where each `|`-delimited phrase serves as the prompt for an individual output frame.
This currently is the sole strategy capable of delivering multiple frames per request.

### simple-one-frame
The strategy of the original `/story/` endpoint.
Returns a single frame based on input parameters (input image, input text). Doesn't
attempt story continuation.

### show-this-frame
A strategy that simply shows a single frame with the given image and text. The
image must be uploaded and available at `<calliope-host>/media`. (Endpoint support to
enable this is forthcoming.)

### continuous-v0
Tries to keep a story going, carrying context from a previous frame, if any,
to a new frame. This works in the manner of an "Exquisite Corpse" exercise,
where each generation blindly adds something new to the story, based only on
the step immediately precedent.

This is largely tuned for the EleutherAI/gpt-neo-2.7B model, so uses very short
text fragments.

Returns a single frame per request.

Is very good at maintaining a relatively coherent stream of consciousness, but
sometimes wanders into legalese, politics, programming, or other topics that
may bore or even offend. EleutherAI/gpt-neo-2.7B isn't trained for political
correctness.

### continuous-v1
Builds on `continuous-v0`, but is meant to be used with larger text prompts
and the GPT-4 and later models.
