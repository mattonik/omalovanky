from __future__ import annotations

import io
import time
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.config import Settings
from app.image_processing import A4_300_DPI, ColoringProcessor
from app.image_provider import GeneratedImage
from app.main import create_app
from app.prompting import build_image_prompt
from app.schemas import GenerationRequest
from app.storage import Storage


def source_png(path: Path, size: tuple[int, int] = (600, 800)) -> None:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((100, 100, size[0] - 100, size[1] - 100), outline="black", width=12)
    image.save(path)


def test_processor_creates_a4_png_and_pdf_in_both_orientations(tmp_path: Path) -> None:
    processor = ColoringProcessor()
    source = tmp_path / "source.png"
    source_png(source)

    for generation_id, orientation in ((1, "portrait"), (2, "landscape")):
        result = processor.process(
            generation_id=generation_id,
            source_path=source,
            output_dir=tmp_path,
            orientation=orientation,
        )
        with Image.open(result.png_path) as image:
            assert image.size == A4_300_DPI[orientation]
            assert image.mode == "1"
        assert result.pdf_path.read_bytes().startswith(b"%PDF")


def test_download_print_and_recent_endpoints(tmp_path: Path) -> None:
    class Provider:
        def generate(self, prompt: str, orientation: str) -> GeneratedImage:
            buffer = io.BytesIO()
            image = Image.new("RGB", (320, 420), "white")
            ImageDraw.Draw(image).rectangle((50, 50, 270, 370), outline="black", width=10)
            image.save(buffer, format="PNG")
            return GeneratedImage(buffer.getvalue(), "req-output")

    settings = Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key_file=tmp_path / "secret",
    )
    with TestClient(create_app(settings, image_provider=Provider(), start_worker=True)) as client:
        response = client.post(
            "/api/generations",
            json={
                "worlds": ["unicorns"],
                "characters": ["unicorn"],
                "action": "riding",
                "orientation": "portrait",
            },
        )
        generation_id = response.json()["id"]
        deadline = time.monotonic() + 5
        item = {}
        while time.monotonic() < deadline:
            item = client.get(f"/api/generations/{generation_id}").json()
            if item["status"] == "done":
                break
            time.sleep(0.02)
        assert item["status"] == "done"
        png = client.get(item["png_url"])
        pdf = client.get(item["pdf_url"])
        print_page = client.get(item["print_url"])
        recent = client.get("/api/colorings")

    assert png.status_code == 200 and png.headers["content-type"].startswith("image/png")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert print_page.status_code == 200 and "window.print()" in print_page.text
    assert recent.json()[0]["id"] == generation_id


def test_prune_keeps_only_twenty_completed_generations(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "app.db")
    storage.init_db()
    request = GenerationRequest(
        worlds=["cars"],
        characters=["lightning-mcqueen"],
        action="racing",
        orientation="landscape",
    )
    created_paths: list[Path] = []
    first_id = 0
    for index in range(21):
        job = storage.create_generation(request, build_image_prompt(request))
        if index == 0:
            first_id = job["id"]
        storage.claim_next_generation()
        paths = []
        for suffix in ("source.png", "png", "pdf"):
            path = tmp_path / f"{job['id']}-{suffix}"
            path.write_bytes(b"x")
            paths.append(path)
            created_paths.append(path)
        storage.mark_generation_done(
            job["id"],
            source_path=str(paths[0]),
            png_path=str(paths[1]),
            pdf_path=str(paths[2]),
            provider_request_id=None,
        )

    stale_paths = storage.prune_completed(keep=20)
    for raw_path in stale_paths:
        Path(raw_path).unlink(missing_ok=True)

    assert len(storage.list_completed(limit=20)) == 20
    assert all(str(path) not in stale_paths for path in created_paths[3:])
    assert all(not Path(path).exists() for path in stale_paths)
    try:
        storage.get_generation(first_id)
    except Exception as exc:
        assert "neexistuje" in str(exc)
    else:
        raise AssertionError("Najstarší záznam mal byť odstránený.")
