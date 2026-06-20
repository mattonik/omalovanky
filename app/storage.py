from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import GenerationRequest


class ActiveGenerationError(RuntimeError):
    pass


class GenerationNotFoundError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
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
                """
            )

    def create_generation(self, request: GenerationRequest, prompt: str) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                "SELECT id FROM generations WHERE status IN ('queued', 'running') LIMIT 1"
            ).fetchone()
            if active is not None:
                connection.rollback()
                raise ActiveGenerationError(
                    f"Generovanie #{active['id']} už prebieha. Počkajte na jeho dokončenie."
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

    def mark_generation_done(
        self,
        generation_id: int,
        *,
        source_path: str,
        provider_request_id: str | None,
        png_path: str | None = None,
        pdf_path: str | None = None,
    ) -> None:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE generations
                SET status = 'done', source_path = ?, provider_request_id = ?,
                    png_path = ?, pdf_path = ?, completed_at = ?, updated_at = ?, error = NULL
                WHERE id = ?
                """,
                (
                    source_path,
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
            return cursor.rowcount

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

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["request"] = json.loads(item.pop("request_json"))
        return item

