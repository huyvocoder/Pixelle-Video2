# Web UI Guide

Detailed introduction to the Pixelle-Video Web interface features.

---

## Interface Layout

The Web interface uses a three-column layout:

- **Left Panel**: Content input and audio settings
- **Middle Panel**: Voice and visual settings  
- **Right Panel**: Video generation and preview
- **Sidebar**: System configuration and FAQ

---

## System Configuration

First-time use requires configuring LLM and image generation services. See [Configuration Guide](../getting-started/configuration.md).

---

## Content Input

### Generation Mode

- **AI Generate Content**: Enter a topic, AI creates script automatically
- **Fixed Script Content**: Enter complete script directly

### Fixed Script Split Mode

When using fixed script mode, you can choose how to split the content:

- **By Paragraph**: Split by empty lines, each paragraph becomes a scene
- **By Line**: Split by line breaks, each line becomes a scene
- **By Sentence**: Smart sentence boundary detection, each sentence becomes a scene

### Background Music

- Built-in music supported
- Custom music files supported

---

## Voice Settings

### TTS Workflow

- Select TTS workflow
- Supports Edge-TTS, Index-TTS, etc.

### Reference Audio

- Upload reference audio for voice cloning
- Supports MP3/WAV/FLAC formats

---

## Visual Settings

### Image/Video Generation

- Select media generation workflow (image or video)
- Adjust prompt prefix to control style

### Video Template

- **Template Preview Gallery**: Visually preview all available templates
- Supports portrait (1080x1920) / landscape (1920x1080) / square (1080x1080)
- Template types:
  - `static_*.html`: Static templates (no AI-generated media)
  - `image_*.html`: Image templates (requires AI-generated images)
  - `video_*.html`: Video templates (requires AI-generated videos)

---

## Generate Video

After clicking "Generate Video", the system will:

1. Generate video script
2. Generate images/videos for each scene
3. Synthesize voice narration
4. Compose final video

Automatically previews when complete.

---

## FAQ

The sidebar includes built-in FAQ for quick reference:

- Common configuration issues
- Generation failure solutions
- Performance optimization tips

