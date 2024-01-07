# Stories

Calliope's central purpose is to tell stories. A story is told something like a graphic
novel, as a sequence of _frames_, where each frame consists of an image and/or a piece
of text. In addition, a frame may have a _trigger condition_, that determines when it
can be shown, and a _minimum duration_, which determines a minimum time span during
which it should be shown.

## Story Strategies

Calliope constructs a story using a story _strategy_. A strategy is a program that
embodies a way of generating frames of a story. As we experiment with different ways
to create stories, we do so by creating new strategies. As such, the list of available
strategies is likely to remain highly dynamic as experimentation continues.

## Current Story Strategies

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
has an unfortunate tendency to wander into nerdy programmery jargon for long
spans of time.

### continuous-v1
Builds on `continuous-v0`, but is meant to be used with larger text prompts
and the GPT-3, GPT-4, etc. models (e.g., `text_to_text_model_config = "openai_curie"`).
