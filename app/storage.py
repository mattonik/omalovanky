from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import ComicRequest, GenerationRequest


class ActiveGenerationError(RuntimeError):
    pass


class GenerationNotFoundError(RuntimeError):
    pass


class ComicNotFoundError(RuntimeError):
    pass


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
            isolation_level=None,
            factory=ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'done', 'failed')),
                    request_json TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    provider_request_id TEXT,
                    source_path TEXT,
                    color_path TEXT,
                    png_path TEXT,
                    pdf_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_generations_status_id
                    ON generations(status, id);
                CREATE INDEX IF NOT EXISTS idx_generations_completed
                    ON generations(status, completed_at DESC, id DESC);

                CREATE TABLE IF NOT EXISTS comic_generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'done', 'failed')),
                    request_json TEXT NOT NULL,
                    prompt_json TEXT NOT NULL,
                    color_pdf_path TEXT,
                    line_art_pdf_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS comic_pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comic_id INTEGER NOT NULL REFERENCES comic_generations(id) ON DELETE CASCADE,
                    page_number INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    provider_request_id TEXT,
                    color_path TEXT,
                    line_art_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(comic_id, page_number)
                );

                CREATE INDEX IF NOT EXISTS idx_comics_status_id
                    ON comic_generations(status, id);
                CREATE INDEX IF NOT EXISTS idx_comics_completed
                    ON comic_generations(status, completed_at DESC, id DESC);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(generations)").fetchall()
            }
            if "color_path" not in columns:
                connection.execute("ALTER TABLE generations ADD COLUMN color_path TEXT")

    def _active_job(self, connection: sqlite3.Connection) -> tuple[str, int] | None:
        active = connection.execute(
            "SELECT id FROM generations WHERE status IN ('queued', 'running') LIMIT 1"
        ).fetchone()
        if active is not None:
            return ("Generovanie", int(active["id"]))
        active = connection.execute(
            "SELECT id FROM comic_generations WHERE status IN ('queued', 'running') LIMIT 1"
        ).fetchone()
        if active is not None:
            return ("Komiks", int(active["id"]))
        return None

    def create_generation(self, request: GenerationRequest, prompt: str) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = self._active_job(connection)
            if active is not None:
                connection.rollback()
                label, active_id = active
                raise ActiveGenerationError(
                    f"{label} #{active_id} už prebieha. Počkajte na jeho dokončenie."
                )
            cursor = connection.execute(
                """
                INSERT INTO generations(status, request_json, prompt, created_at, updated_at)
                VALUES ('queued', ?, ?, ?, ?)
                """,
                (request.model_dump_json(), prompt, now, now),
            )
            generation_id = int(cursor.lastrowid)
            connection.commit()
        return self.get_generation(generation_id)

    def create_comic(self, request: ComicRequest, prompts: list[str]) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = self._active_job(connection)
            if active is not None:
                connection.rollback()
                label, active_id = active
                raise ActiveGenerationError(
                    f"{label} #{active_id} už prebieha. Počkajte na jeho dokončenie."
                )
            cursor = connection.execute(
                """
                INSERT INTO comic_generations(status, request_json, prompt_json, created_at, updated_at)
                VALUES ('queued', ?, ?, ?, ?)
                """,
                (request.model_dump_json(), json.dumps(prompts), now, now),
            )
            comic_id = int(cursor.lastrowid)
            connection.executemany(
                """
                INSERT INTO comic_pages(comic_id, page_number, prompt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [(comic_id, index, prompt, now, now) for index, prompt in enumerate(prompts, 1)],
            )
            connection.commit()
        return self.get_comic(comic_id)

    def get_generation(self, generation_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM generations WHERE id = ?",
                (generation_id,),
            ).fetchone()
        if row is None:
            raise GenerationNotFoundError(f"Generovanie #{generation_id} neexistuje.")
        return self._row_to_dict(row)

    def claim_next_generation(self) -> dict[str, Any] | None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM generations WHERE status = 'queued' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            generation_id = int(row["id"])
            connection.execute(
                """
                UPDATE generations
                SET status = 'running', started_at = ?, updated_at = ?, error = NULL
                WHERE id = ? AND status = 'queued'
                """,
                (now, now, generation_id),
            )
            connection.commit()
        return self.get_generation(generation_id)

    def claim_next_comic(self) -> dict[str, Any] | None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM comic_generations WHERE status = 'queued' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            comic_id = int(row["id"])
            connection.execute(
                """
                UPDATE comic_generations
                SET status = 'running', started_at = ?, updated_at = ?, error = NULL
                WHERE id = ? AND status = 'queued'
                """,
                (now, now, comic_id),
            )
            connection.commit()
        return self.get_comic(comic_id)

    def mark_generation_done(
        self,
        generation_id: int,
        *,
        source_path: str,
        color_path: str | None = None,
        provider_request_id: str | None,
        png_path: str | None = None,
        pdf_path: str | None = None,
    ) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE generations
                SET status = 'done', source_path = ?, color_path = ?, provider_request_id = ?,
                    png_path = ?, pdf_path = ?, completed_at = ?, updated_at = ?, error = NULL
                WHERE id = ?
                """,
                (
                    source_path,
                    color_path,
                    provider_request_id,
                    png_path,
                    pdf_path,
                    now,
                    now,
                    generation_id,
                ),
            )

    def mark_generation_failed(self, generation_id: int, error: str) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE generations
                SET status = 'failed', error = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (error[:2000], now, now, generation_id),
            )

    def mark_comic_page_done(
        self,
        comic_id: int,
        page_number: int,
        *,
        provider_request_id: str | None,
        color_path: str,
        line_art_path: str,
    ) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE comic_pages
                SET provider_request_id = ?, color_path = ?, line_art_path = ?, updated_at = ?
                WHERE comic_id = ? AND page_number = ?
                """,
                (provider_request_id, color_path, line_art_path, now, comic_id, page_number),
            )

    def mark_comic_done(
        self,
        comic_id: int,
        *,
        color_pdf_path: str,
        line_art_pdf_path: str,
    ) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE comic_generations
                SET status = 'done', color_pdf_path = ?, line_art_pdf_path = ?,
                    completed_at = ?, updated_at = ?, error = NULL
                WHERE id = ?
                """,
                (color_pdf_path, line_art_pdf_path, now, now, comic_id),
            )

    def mark_comic_failed(self, comic_id: int, error: str) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE comic_generations
                SET status = 'failed', error = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (error[:2000], now, now, comic_id),
            )

    def recover_interrupted_generations(self) -> int:
        now = utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE generations
                SET status = 'queued', started_at = NULL, updated_at = ?,
                    error = 'Úloha bola obnovená po reštarte aplikácie.'
                WHERE status = 'running'
                """,
                (now,),
            )
            generation_count = cursor.rowcount
            cursor = connection.execute(
                """
                UPDATE comic_generations
                SET status = 'queued', started_at = NULL, updated_at = ?,
                    error = 'Úloha bola obnovená po reštarte aplikácie.'
                WHERE status = 'running'
                """,
                (now,),
            )
            return generation_count + cursor.rowcount

    def list_completed(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM generations
                WHERE status = 'done' AND png_path IS NOT NULL
                ORDER BY completed_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_comic(self, comic_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM comic_generations WHERE id = ?",
                (comic_id,),
            ).fetchone()
            if row is None:
                raise ComicNotFoundError(f"Komiks #{comic_id} neexistuje.")
            pages = connection.execute(
                "SELECT * FROM comic_pages WHERE comic_id = ? ORDER BY page_number",
                (comic_id,),
            ).fetchall()
        return self._comic_row_to_dict(row, pages)

    def list_completed_comics(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM comic_generations
                WHERE status = 'done' AND line_art_pdf_path IS NOT NULL
                ORDER BY completed_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            comics = []
            for row in rows:
                pages = connection.execute(
                    "SELECT * FROM comic_pages WHERE comic_id = ? ORDER BY page_number",
                    (row["id"],),
                ).fetchall()
                comics.append(self._comic_row_to_dict(row, pages))
        return comics

    def prune_completed(self, keep: int = 20) -> list[str]:
        # Historical method kept for compatibility; we no longer delete
        # completed generations so every created coloring remains on disk.
        return []

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["request"] = json.loads(item.pop("request_json"))
        return item

    def _comic_row_to_dict(
        self,
        row: sqlite3.Row,
        pages: list[sqlite3.Row],
    ) -> dict[str, Any]:
        item = dict(row)
        item["request"] = json.loads(item.pop("request_json"))
        item["prompts"] = json.loads(item.pop("prompt_json"))
        item["pages"] = [dict(page) for page in pages]
        return item
