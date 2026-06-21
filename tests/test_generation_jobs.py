from __future__ import annotations

import io
import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.image_provider import GeneratedImage
from app.main import create_app
from app.prompting import build_image_prompt
from app.schemas import GenerationRequest
from app.storage import Storage
from app.worker import GenerationWorker

def make_png_bytes(size: tuple[int, int] = (320, 420)) -> bytes:
    image = Image.new("RGB", size, "white")
    for x in range(40, size[0] - 40):
        image.putpixel((x, 80), (0, 0, 0))
        image.putpixel((x, size[1] - 80), (0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class FakeImageProvider:
    def __init__(self, content: bytes | None = None) -> None:
        self.content = content or make_png_bytes()
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, orientation: str) -> GeneratedImage:
        self.calls.append((prompt, orientation))
        return GeneratedImage(self.content, request_id="req-test-123")


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key="test-api-key",
    )


def valid_payload() -> dict:
    return {
        "worlds": ["cars"],
        "characters": ["lightning-mcqueen", "mater"],
        "action": "racing",
        "custom_idea": "pretekajú po širokej ceste",
        "orientation": "landscape",
    }


def test_api_rejects_second_active_generation(tmp_path: Path) -> None:
    with TestClient(
        create_app(make_settings(tmp_path), image_provider=FakeImageProvider(), start_worker=False)
    ) as client:
        first = client.post("/api/generations", json=valid_payload())
        second = client.post("/api/generations", json=valid_payload())

    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "generation_in_progress"


def test_worker_generates_source_image_and_marks_job_done(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    provider = FakeImageProvider()
    storage = Storage(settings.db_path)
    storage.init_db()
    request = GenerationRequest.model_validate(valid_payload())
    job = storage.create_generation(request, build_image_prompt(request))
    worker = GenerationWorker(
        storage=storage,
        image_provider=provider,
        colorings_dir=settings.colorings_dir,
    )

    assert worker.process_one() is True

    completed = storage.get_generation(job["id"])
    assert completed["status"] == "done"
    assert completed["provider_request_id"] == "req-test-123"
    assert Path(completed["source_path"]).read_bytes() == provider.content
    assert Path(completed["png_path"]).is_file()
    assert Path(completed["pdf_path"]).is_file()
    assert provider.calls[0][1] == "landscape"


def test_running_generation_is_requeued_after_restart(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    storage = Storage(settings.db_path)
    storage.init_db()
    request = GenerationRequest.model_validate(valid_payload())
    job = storage.create_generation(request, build_image_prompt(request))
    claimed = storage.claim_next_generation()
    assert claimed and claimed["status"] == "running"

    recovered = storage.recover_interrupted_generations()

    assert recovered == 1
    assert storage.get_generation(job["id"])["status"] == "queued"


def test_background_worker_processes_api_job(tmp_path: Path) -> None:
    provider = FakeImageProvider()
    with TestClient(
        create_app(make_settings(tmp_path), image_provider=provider, start_worker=True)
    ) as client:
        response = client.post("/api/generations", json=valid_payload())
        generation_id = response.json()["id"]
        deadline = time.monotonic() + 3
        status_payload = {}
        while time.monotonic() < deadline:
            status_payload = client.get(f"/api/generations/{generation_id}").json()
            if status_payload["status"] == "done":
                break
            time.sleep(0.02)

    assert status_payload["status"] == "done"
    assert status_payload["png_url"] == f"/colorings/{generation_id}.png"
    assert status_payload["pdf_url"] == f"/colorings/{generation_id}.pdf"
    assert status_payload["color_url"] == f"/colorings/{generation_id}/color.png"
    assert status_payload["pattern_print_url"] == f"/colorings/{generation_id}/print-pattern"
    assert len(provider.calls) == 1
