# Calliope

![image](https://user-images.githubusercontent.com/17924059/209908360-af2a806e-e121-4f39-a988-72c3b73142db.png)

(A Calliope self-portrait)

In Greek mythology, Calliope (/kəˈlaɪ.əpi/ kə-LY-ə-pee; Ancient Greek: Καλλιόπη, romanized: Kalliópē, lit. 'beautiful-voiced') is the Muse who presides over eloquence and epic poetry; so called from the ecstatic harmony of her voice. Hesiod and Ovid called her the "Chief of all Muses".

Calliope is a framework meant to make modern AI tools like generative AI (large language models and image generation models), computer vision, and vector databases accessible for use by artists creating interactive art works. The core system is a flexible framework, service, and API that enables an artist to build repeatable interaction strategies. The API can accept inputs such as images, text, and voice, then process these through an artist-defined pipeline of AI models to generate text and image output.

The focus is on enabling the creation of works that are "aware" of the environment in which they are installed or running, in the sense that they can see, hear, and react to things or people in that environment. This is currently limited to image input, such as from a Webcam, but the hope is to extend that to cover audio input as well, including speech recognition.

* Processing is driven by pluggable modules called _story strategies_, meant to be experimented with and extended by the artist-engineers who make use of the framework.

* AI models can be either commercial or open models accessed via APIs (HuggingFace, OpenAI, Stability, Replicate, Azure, etc.) or locally or cloud hosted open source and/or fine-tuned models. (GPT-4, GPT-3, Stable Diffusion, DALL-E 2, MiniGPT-4, LLaMa 2, Claude, FLAN, etc.)

* Images are interpreted by a combination of a multimodal LLM (MiniGPT-4) and the Azure computer vision API to generate a rich text description, lists of recognized objects and text, and metadata that can be passed to other components as input.

* Large language model prompts are stored, manipulated, and applied along with the other processing modules in graphs (prompt chaining) that can be pre-programmed or dynamically created at runtime.  LLMs are driven via LangChain (although this isn't central to the framework).

* A semantic search facility is provided using the Pinecone vector database, with a scheduled ETL pipeline to index generated media.

In this present incarnation, Calliope invents and recites stories. This can be through any client of
its story API. The two existing clients are:
* An [ESP32-Sparrow](https://github.com/mikalhart/ESP32-Sparrow) -- one of a family of bespoke hardware devices with a screen and optional input sensors such as camera and microphone.
* [Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md) -- a small TypeScript client included in this repo, runnable in any browser on desktop or mobile devices. Clio accepts image input from any accessible webcam and passes this with its request for a story continuation. Calliope uses this input to condition its continuation of the story.


## Try it Out!
You can try Calliope and Clio at [https://calliope.chrisimmel.com/clio/](https://calliope.chrisimmel.com/clio/).

<img src="https://github.com/chrisimmel/calliope/assets/17924059/7e4f77b0-4bbb-4aba-ba42-4914c580b6d1" alt="drawing" height="400"/>


Hints:
* Clio constructs a story for you, one frame at a time. You request a new frame by swiping to the left. You can review previous frames by swiping to the right. (Clicking the arrows also works.)
* It will ask to access your camera. If you grant it access, it will take a shot of whatever is in the camera view each time you request a new story frame, and use whatever it sees to inform the story.
* You can choose which camera to use from the menu at the lower right:

<img src="https://github.com/chrisimmel/calliope/assets/17924059/bcb62949-0aa9-4470-8801-52b341ab584f" alt="drawing" width="200"/>

If you're on a mobile device, the back camera is the one facing away from you, and is used by default. The front camera is the one facing you.
* Input images are not kept on the Calliope server, so you don't need to worry about it collecting a cache of your photos! (It analyzes the input image, then forgets it, where it is deleted when the ephemeral file storage is cleaned up.)
* You can also turn the camera off from this same menu.
* The default strategy is chosen to give the best results for most people most of the time, but you can also experiment with choosing different strategies from the menu. If you change the strategy and request a new frame, a new story is begun using the new strategy.


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
