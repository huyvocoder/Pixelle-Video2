# API Usage

Pixelle-Video provides a complete Python API for easy integration into your projects.

---

## Quick Start

```python
from pixelle_video.service import PixelleVideoCore
import asyncio

async def main():
    # Initialize
    pixelle = PixelleVideoCore()
    await pixelle.initialize()
    
    # Generate video
    result = await pixelle.generate_video(
        text="Why develop a reading habit",
        mode="generate",
        n_scenes=5
    )
    
    print(f"Video generated: {result.video_path}")

# Run
asyncio.run(main())
```

---

## API Reference

For detailed API documentation, see [API Overview](../reference/api-overview.md).

---

## Examples

For more usage examples, check the `examples/` directory in the project.

