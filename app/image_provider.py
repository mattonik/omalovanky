from __future__ import annotations

import base64
from dataclasses import dataclass
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
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def _read_api_key(self) -> str:
        api_key = (self.api_key or "").strip()
        if not api_key:
            raise RuntimeError("Premenná OPENAI_API_KEY nie je nastavená.")
        return api_key

    def generate(self, prompt: str, orientation: Orientation) -> GeneratedImage:
        client = OpenAI(api_key=self._read_api_key())
        size = "1024x1536" if orientation == "portrait" else "1536x1024"
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
