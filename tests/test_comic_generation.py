from __future__ import annotations

import io
import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import Settings
from app.image_processing import ComicProcessor
from app.image_provider import GeneratedImage
from app.main import create_app
from app.prompting import build_comic_page_prompts
from app.schemas import ComicRequest
from app.storage import Storage
from app.worker import GenerationWorker


def make_color_page(index: int) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (640, 640), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 560, 560), outline=(80 + index * 20, 110, 220), width=16)
    draw.ellipse((220, 220, 420, 420), fill=(255, 210 - index * 10, 90))
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class ComicProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, orientation: str) -> GeneratedImage:
        self.calls.append((prompt, orientation))
        return GeneratedImage(make_color_page(len(self.calls)), f"req-comic-{len(self.calls)}")

    def edit(self, source_path: Path, prompt: str, orientation: str) -> GeneratedImage:
        return self.generate(prompt, orientation)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key="test-api-key",
    )


def valid_comic_payload() -> dict:
    return {
        "worlds": ["cars"],
        "characters": ["lightning-mcqueen", "mater"],
        "story_type": "race",
        "custom_idea": "pretekajú a pomôžu kamarátovi",
        "primary_mode": "line_art",
    }


def test_comic_worker_generates_pages_and_booklet_pdfs(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    storage = Storage(settings.db_path)
    storage.init_db()
    provider = ComicProvider()
    request = ComicRequest.model_validate(valid_comic_payload())
    comic = storage.create_comic(request, build_comic_page_prompts(request))
    worker = GenerationWorker(
        storage=storage,
        image_provider=provider,
        colorings_dir=settings.colorings_dir,
    )

    assert worker.process_one() is True

    completed = storage.get_comic(comic["id"])
    assert completed["status"] == "done"
    assert len(completed["pages"]) == 6
    assert len(provider.calls) == 6
    assert all(call[1] == "landscape" for call in provider.calls)
    assert Path(completed["color_pdf_path"]).read_bytes().startswith(b"%PDF")
    assert Path(completed["line_art_pdf_path"]).read_bytes().startswith(b"%PDF")
    assert all(Path(page["color_path"]).is_file() for page in completed["pages"])
    assert all(Path(page["line_art_path"]).is_file() for page in completed["pages"])


def test_comic_api_flow_and_downloads(tmp_path: Path) -> None:
    provider = ComicProvider()
    with TestClient(create_app(make_settings(tmp_path), image_provider=provider, start_worker=True)) as client:
        response = client.post("/api/comics", json=valid_comic_payload())
        assert response.status_code == 202
        comic_id = response.json()["id"]
        deadline = time.monotonic() + 5
        item = {}
        while time.monotonic() < deadline:
            item = client.get(f"/api/comics/{comic_id}").json()
            if item["status"] == "done":
                break
            time.sleep(0.02)
        color_pdf = client.get(item["color_pdf_url"])
        line_art_pdf = client.get(item["line_art_pdf_url"])
        first_page = client.get(item["pages"][0]["line_art_url"])
        recent = client.get("/api/comics")

    assert item["status"] == "done"
    assert len(item["pages"]) == 6
    assert color_pdf.status_code == 200 and color_pdf.content.startswith(b"%PDF")
    assert line_art_pdf.status_code == 200 and line_art_pdf.content.startswith(b"%PDF")
    assert first_page.status_code == 200 and first_page.headers["content-type"].startswith("image/png")
    assert recent.json()[0]["id"] == comic_id


def test_comic_rejects_second_active_job(tmp_path: Path) -> None:
    with TestClient(
        create_app(make_settings(tmp_path), image_provider=ComicProvider(), start_worker=False)
    ) as client:
        first = client.post("/api/comics", json=valid_comic_payload())
        second = client.post("/api/generations", json={
            "worlds": ["cars"],
            "characters": ["lightning-mcqueen"],
            "action": "racing",
            "orientation": "landscape",
        })

    assert first.status_code == 202
    assert second.status_code == 409


def test_comic_processor_requires_exactly_six_pages(tmp_path: Path) -> None:
    processor = ComicProcessor()
    page = tmp_path / "page.png"
    page.write_bytes(make_color_page(1))

    try:
        processor.create_mini_zine(
            comic_id=1,
            color_paths=[page] * 5,
            line_art_paths=[page] * 6,
            output_dir=tmp_path,
        )
    except ValueError as exc:
        assert "presne 6" in str(exc)
    else:
        raise AssertionError("Expected invalid comic page count to fail.")


def test_comic_page_routes_validate_page_range(tmp_path: Path) -> None:
    provider = ComicProvider()
    with TestClient(create_app(make_settings(tmp_path), image_provider=provider, start_worker=True)) as client:
        response = client.post("/api/comics", json=valid_comic_payload())
        comic_id = response.json()["id"]
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            item = client.get(f"/api/comics/{comic_id}").json()
            if item["status"] == "done":
                break
            time.sleep(0.02)
        too_low = client.get(f"/comics/{comic_id}/pages/0/color.png")
        too_high = client.get(f"/comics/{comic_id}/pages/7/line-art.png")

    assert too_low.status_code == 422
    assert too_high.status_code == 422


def test_running_comic_is_requeued_after_restart(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    storage = Storage(settings.db_path)
    storage.init_db()
    request = ComicRequest.model_validate(valid_comic_payload())
    comic = storage.create_comic(request, build_comic_page_prompts(request))
    claimed = storage.claim_next_comic()
    assert claimed and claimed["status"] == "running"

    recovered = storage.recover_interrupted_generations()

    assert recovered == 1
    assert storage.get_comic(comic["id"])["status"] == "queued"


def test_requeued_comic_reuses_existing_page_files(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    storage = Storage(settings.db_path)
    storage.init_db()
    provider = ComicProvider()
    request = ComicRequest.model_validate(valid_comic_payload())
    comic = storage.create_comic(request, build_comic_page_prompts(request))
    comic_id = comic["id"]
    comic_dir = settings.colorings_dir / f"comic-{comic_id}"
    comic_dir.mkdir(parents=True)
    color_path = comic_dir / "page-1-color.png"
    line_art_path = comic_dir / "page-1-line-art.png"
    color_path.write_bytes(make_color_page(1))
    line_art_path.write_bytes(make_color_page(1))
    storage.claim_next_comic()
    storage.mark_comic_page_done(
        comic_id,
        1,
        provider_request_id="existing-page",
        color_path=str(color_path),
        line_art_path=str(line_art_path),
    )
    assert storage.recover_interrupted_generations() == 1
    worker = GenerationWorker(
        storage=storage,
        image_provider=provider,
        colorings_dir=settings.colorings_dir,
    )

    assert worker.process_one() is True

    completed = storage.get_comic(comic_id)
    assert completed["status"] == "done"
    assert len(provider.calls) == 5
    assert completed["pages"][0]["provider_request_id"] == "existing-page"
