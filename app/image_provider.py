from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from openai import OpenAI

from .schemas import Orientation


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    content: bytes
    request_id: str | None = None


class ImageProvider(Protocol):
    def generate(self, prompt: str, orientation: Orientation) -> GeneratedImage: ...


class OpenAIImageProvider:
    def __init__(self, api_key_file: Path) -> None:
        self.api_key_file = api_key_file

    def _read_api_key(self) -> str:
        try:
            api_key = self.api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(
                f"OpenAI secret sa nepodarilo načítať zo súboru {self.api_key_file}."
            ) from exc
        if not api_key:
            raise RuntimeError("OpenAI secret je prázdny.")
        return api_key

    def generate(self, prompt: str, orientation: Orientation) -> GeneratedImage:
        client = OpenAI(api_key=self._read_api_key())
        size = "1024x1440" if orientation == "portrait" else "1440x1024"
        result = client.images.generate(
            model="gpt-image-2",
            prompt=prompt,
            n=1,
            size=size,
            quality="medium",
            output_format="png",
            background="opaque",
            moderation="auto",
        )
        if not result.data or not result.data[0].b64_json:
            raise RuntimeError("OpenAI nevrátil dáta obrázka.")
        return GeneratedImage(
            content=base64.b64decode(result.data[0].b64_json),
            request_id=getattr(result, "_request_id", None),
        )

