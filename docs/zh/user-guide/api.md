# API 使用

Pixelle-Video 提供完整的 Python API，方便集成到你的项目中。

---

## 快速开始

```python
from pixelle_video.service import PixelleVideoCore
import asyncio

async def main():
    # 初始化
    pixelle = PixelleVideoCore()
    await pixelle.initialize()
    
    # 生成视频
    result = await pixelle.generate_video(
        text="为什么要养成阅读习惯",
        mode="generate",
        n_scenes=5
    )
    
    print(f"视频已生成: {result.video_path}")

# 运行
asyncio.run(main())
```

---

## API 参考

详细 API 文档请查看 [API 概览](../reference/api-overview.md)。

---

## 示例

更多使用示例请参考项目的 `examples/` 目录。

