# Calliope

![image](https://user-images.githubusercontent.com/17924059/209908360-af2a806e-e121-4f39-a988-72c3b73142db.png)

(A Calliope self-portrait)

In Greek mythology, Calliope (/kəˈlaɪ.əpi/ kə-LY-ə-pee; Ancient Greek: Καλλιόπη, romanized: Kalliópē, lit. 'beautiful-voiced') is the Muse who presides over eloquence and epic poetry; so called from the ecstatic harmony of her voice. Hesiod and Ovid called her the "Chief of all Muses".

Calliope is an experimental framework that brings modern AI tools like generative AI (large language models and image generation models), computer vision, and vector databases into the service of the creation of interactive art works. The core system is a flexible framework, service, and API that enables an artist to build repeatable interaction strategies. The API can accept inputs such as images, text, and voice, then process these through an artist-defined pipeline of AI models to generate text and image output.

The focus is on enabling the creation of works that are "aware" of the environment in which they are installed or running, in the sense that they can see, hear, and react to things or people in that environment. This is currently limited to image input, such as from a Webcam, but the hope is to extend that to cover audio input as well, including speech recognition.

* Processing is driven by pluggable modules called _story strategies_  (or "storytellers" in Clio parlance), meant to be experimented with and extended by the artist-engineers who make use of the framework.

* AI models can be any commercial or open source models accessible by API. Examples include providers include OpenAI, Anthropic, HuggingFace, Stability, Replicate, Runway, Azure.

* Images are interpreted by a combination of a multimodal LLM (GPT-4o, Claude, Gemini) and the Azure computer vision API to generate a rich text description, lists of recognized objects and text, and metadata that can be passed to other components as input.

* Large language model prompts are stored, manipulated, and applied along with the other processing modules in graphs (prompt chaining) that can be pre-programmed or dynamically created at runtime.  LLMs are driven via LangChain (although this isn't central to the framework).

* A semantic search facility is provided using the Pinecone vector database, with a scheduled ETL pipeline to index generated media.

There is a strong emphasis on narrative structure. Calliope invents and recites stories. This can be through any client of
its `story` API. The two existing clients are:
* An [ESP32-Sparrow](https://github.com/mikalhart/ESP32-Sparrow) -- one of a family of bespoke hardware devices with a screen and optional input sensors such as camera and microphone.
* [Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md) -- a small TypeScript client included in this repo, runnable in any browser on desktop or mobile devices. Clio accepts image input from any accessible webcam and passes this with its request for a story continuation. Calliope uses this input to condition its continuation of the story.


## Try it Out!
You can try Calliope and Clio at [https://calliope.chrisimmel.com/clio/](https://calliope.chrisimmel.com/clio/).

![image](https://github.com/chrisimmel/calliope/assets/17924059/1c921993-9c3a-45a2-a6e5-f565933a4dc2)


Hints:
* Clio works with "storytellers" in Calliope to construct a story for you, one frame at a time. You request a new frame by tapping any of the buttons at the bottom of the screen.
  * Click the <img src="https://github.com/chrisimmel/calliope/assets/17924059/a54ca8db-96a3-4024-b88f-165294ba3de1" alt="plus" width="30"> (plus) icon to let the storyteller simply continue along its current train of thought.
  * Click the <img src="https://github.com/chrisimmel/calliope/assets/17924059/dac8bfa2-1e84-4a2b-a94e-a7e6e6285212" alt="microphone" width="30" style="margin-bottom: -4px"> (microphone) icon and speak a few words to give the storyteller an idea or inspiration.
  * Click the <img src="https://github.com/chrisimmel/calliope/assets/17924059/907bd4ea-87fc-4831-a0a6-f553f06e3bbd" alt="camera" width="30" style="margin-bottom: -4px"> (camera) icon to take a photo and send it to the storyteller for inspiration.
* After you do this, Calliope will work for several seconds and give you a new frame.
* You can review previous frames by swiping to the right. (Clicking the arrows also works.)
* Input images and sounds are not kept on the Calliope server, so you don't need to worry about it hording a cache of your photos and soundlclips!

* You can start a new story at any time from the menu. The "Create New Story" option lets you start a new story using the storyteller of your choice, from either a photo, a spoken sound clip, or "thin air".
* You can browse stories you've created in the past and select them to either review or update them.
* Coming soon:
  * Bookmark stories and share them with friends.


## Table of Contents

- [Building](https://github.com/chrisimmel/calliope/tree/main/docs/building.md)
- [Running](https://github.com/chrisimmel/calliope/tree/main/docs/running.md)
- [API](https://github.com/chrisimmel/calliope/tree/main/docs/api.md)
- [Stories](https://github.com/chrisimmel/calliope/tree/main/docs/stories.md)
- [Configuration](https://github.com/chrisimmel/calliope/tree/main/docs/config.md)
- [Scheduling](https://github.com/chrisimmel/calliope/tree/main/docs/scheduling.md)
- [Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md)
- [Thoth](https://github.com/chrisimmel/calliope/tree/main/docs/Thoth.md)
- [Storage](https://github.com/chrisimmel/calliope/tree/main/docs/storage.md)
- [Calliope Admin](https://github.com/chrisimmel/calliope/tree/main/docs/Admin.md)
