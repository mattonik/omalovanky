from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    colorings_dir: Path
    openai_api_key: str | None = field(repr=False)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("APP_DB_PATH", "./data/app.db")).expanduser(),
            colorings_dir=Path(os.getenv("COLORINGS_DIR", "./data/colorings")).expanduser(),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

    @property
    def has_openai_api_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())


settings = Settings.from_env()
