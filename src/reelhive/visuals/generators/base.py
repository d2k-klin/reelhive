from pathlib import Path
from typing import Protocol


class ImageGenerator(Protocol):
    def generate(self, prompt: str, size: str, output: Path) -> dict: ...
