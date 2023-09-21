# Calliope

![image](https://user-images.githubusercontent.com/17924059/209908360-af2a806e-e121-4f39-a988-72c3b73142db.png)

(A Calliope self-portrait)

In Greek mythology, Calliope (/kəˈlaɪ.əpi/ kə-LY-ə-pee; Ancient Greek: Καλλιόπη, romanized: Kalliópē, lit. 'beautiful-voiced') is the Muse who presides over eloquence and epic poetry; so called from the ecstatic harmony of her voice. Hesiod and Ovid called her the "Chief of all Muses".

Calliope is a framework meant to make modern AI tools like generative AI (large language models and image generation models), computer vision, and vector databases accessible for use by artists creating interactive art works. The core system is a flexible framework, service, and API that enables an artist to build repeatable interaction strategies. The API can accept inputs such as images, text, and voice, then process these through an artist-defined pipeline of AI models to generate text and image output.

* AI models can be either commercial or open models accessed via APIs (HuggingFace, OpenAI, Stability, Replicate, Azure, etc.) or locally or cloud hosted open source and/or fine-tuned models. (GPT-4, GPT-3, Stable Diffusion, DALL-E, MiniGPT-4, LLaMa 2, etc.)

* Images are interpreted by a combination of a multimodal LLM (MiniGPT-4) and the Azure computer vision API to generate a rich text description, lists of recognized objects and text, and metadata that can be passed to other components as input.

* Large language model prompts are stored, manipulated, and applied along with the other processing modules in graphs (prompt chaining) that can be pre-programmed or dynamically created at runtime.  LLMs are driven via LangChain (although this isn't central to the framework).

* A semantic search facility is provided using the Pinecone vector database, with a scheduled ETL pipeline to index generated media.

In this present incarnation, Calliope invents and recites stories. This can be through any client of
its story API. The two existing clients are:
* An [ESP32-Sparrow](https://github.com/mikalhart/ESP32-Sparrow) -- one of a family of bespoke hardware devices with a screen and optional input sensors such as camera and microphone.
* [Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md) -- a small TypeScript client included in this repo, runnable in any browser on desktop or mobile devices. Clio accepts image input from any accessible webcam and passes this with its request for a story continuation. Calliope uses this input to condition its continuation of the story.

## Table of Contents

- [Building](https://github.com/chrisimmel/calliope/tree/main/docs/building.md)
- [Running](https://github.com/chrisimmel/calliope/tree/main/docs/running.md)
- [API](https://github.com/chrisimmel/calliope/tree/main/docs/api.md)
- [Stories](https://github.com/chrisimmel/calliope/tree/main/docs/stories.md)
- [Configuration](https://github.com/chrisimmel/calliope/tree/main/docs/config.md)
- [Scheduling](https://github.com/chrisimmel/calliope/tree/main/docs/scheduling.md)
- [Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md)
- [Thoth](https://github.com/chrisimmel/calliope/tree/main/docs/Thoth.md)
