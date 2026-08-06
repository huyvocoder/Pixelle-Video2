# Configuration

After installation, you need to configure services to use Pixelle-Video.

---

## LLM Configuration

LLM (Large Language Model) is used to generate video scripts.

### Quick Preset Selection

1. Select a preset model from the dropdown:
   - Qianwen (recommended, great value)
   - GPT-4o
   - DeepSeek
   - Ollama (local, completely free)

2. The system will auto-fill `base_url` and `model`

3. Click「🔑 Get API Key」to register and obtain credentials

4. Enter your API Key

---

## Image/Video Generation Configuration

Two options available:

### Local Deployment

Using local ComfyUI service:

1. Install and start ComfyUI
2. Enter ComfyUI URL (default `http://127.0.0.1:8188`)
3. Click "Test Connection" to verify
4. (Optional) Enter ComfyUI API Key (get from [Comfy Platform](https://platform.comfy.org/profile/api-keys))

### Cloud Deployment (Recommended)

Using RunningHub cloud service, no local GPU required:

1. Register for a RunningHub account
2. Obtain API Key
3. Enter API Key in configuration
4. Configure advanced options (optional):
   - **Concurrent Limit**: Set number of simultaneous tasks (1-10, default 1 for regular members)
   - **Instance Type**: Choose 24GB or 48GB VRAM machine (48GB for large video generation)

---

## Save Configuration

After filling in all required configuration, click the "Save Configuration" button.

Configuration will be saved to `config.yaml` file.

---

## Next Steps

- [Quick Start](quick-start.md) - Create your first video

