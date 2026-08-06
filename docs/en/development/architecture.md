# Architecture

Technical architecture overview of Pixelle-Video.

---

## Core Architecture

Pixelle-Video uses a layered architecture design:

- **Web Layer**: Streamlit Web interface
- **Service Layer**: Core business logic
- **ComfyUI Layer**: Image and TTS generation

---

## Main Components

### PixelleVideoCore

Core service class coordinating all sub-services.

### LLM Service

Responsible for calling large language models to generate scripts.

### Image Service

Responsible for calling ComfyUI to generate images.

### TTS Service

Responsible for calling ComfyUI to generate speech.

### Video Generator

Responsible for composing the final video.

---

## Tech Stack

- **Backend**: Python 3.10+, AsyncIO
- **Web**: Streamlit
- **AI**: OpenAI API, ComfyUI
- **Configuration**: YAML
- **Tools**: uv (package management)

---

## More Information

Detailed architecture documentation coming soon.

