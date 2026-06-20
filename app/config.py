from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    colorings_dir: Path
    openai_api_key_file: Path

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("APP_DB_PATH", "./data/app.db")).expanduser(),
            colorings_dir=Path(os.getenv("COLORINGS_DIR", "./data/colorings")).expanduser(),
            openai_api_key_file=Path(
                os.getenv("OPENAI_API_KEY_FILE", "/run/secrets/openai_api_key")
            ).expanduser(),
        )

    @property
    def has_openai_secret(self) -> bool:
        try:
            return bool(self.openai_api_key_file.read_text(encoding="utf-8").strip())
        except OSError:
            return False


settings = Settings.from_env()

