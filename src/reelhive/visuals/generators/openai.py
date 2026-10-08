from __future__ import annotations

import base64
from pathlib import Path

from reelhive.config import ImageGeneration


class OpenAIImageGenerator:
    def __init__(self, config: ImageGeneration):
        from openai import OpenAI

        self.config = config
        self.client = OpenAI()

    def generate(self, prompt: str, size: str, output: Path) -> dict:
        result = self.client.images.generate(model=self.config.model, prompt=prompt, size=size, n=1)
        if not result.data or not result.data[0].b64_json:
            raise ValueError("image API returned no base64 image")
        output.write_bytes(base64.b64decode(result.data[0].b64_json, validate=True))
        return {"cost_usd": self.config.cost_per_image, "usage": result.usage.model_dump() if result.usage else {}}
