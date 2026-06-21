from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest
import requests
import uvicorn
from PIL import Image
from playwright.sync_api import sync_playwright

from app.config import Settings
from app.image_provider import GeneratedImage
from app.main import create_app

pytestmark = pytest.mark.e2e

if os.getenv("RUN_E2E") != "1":
    pytest.skip("Set RUN_E2E=1 to run browser tests.", allow_module_level=True)


class FixtureImageProvider:
    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def generate(self, prompt: str, orientation: str) -> GeneratedImage:
        return GeneratedImage(self.fixture_path.read_bytes(), "req-e2e-fixture")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def live_app(tmp_path: Path):
    fixture = Path(__file__).parent / "fixtures" / "sample-coloring.png"
    settings = Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key="test-api-key",
    )
    app = create_app(
        settings,
        image_provider=FixtureImageProvider(fixture),
        start_worker=True,
    )
    port = find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{base_url}/healthz", timeout=0.2).status_code == 200:
                break
        except requests.RequestException:
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("E2E server did not start.")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


def test_builder_to_printable_result_flow(live_app: str, tmp_path: Path) -> None:
    console_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1449, "height": 1086})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.goto(live_app, wait_until="networkidle")

        page.get_by_role("button", name="Bleskový McQueen").click()
        page.get_by_role("button", name="Mater / Burák").click()
        page.get_by_role("button", name="Pretekajú").click()
        page.get_by_role("button", name="Na šírku").click()
        page.get_by_label("Vlastný nápad").fill("Bleskový McQueen a Mater pretekajú spolu")
        page.get_by_role("button", name="Vytvoriť omaľovánku").click()

        page.get_by_role("heading", name="Hotovo! Môžeme vyfarbovať.").wait_for(timeout=10_000)
        page.locator("#resultImage").wait_for(state="visible")
        page.locator("#resultImage").evaluate(
            "(image) => image.complete && image.naturalWidth > 0"
        )

        assert page.get_by_role("link", name="Vytlačiť bez vzoru").is_visible()
        assert page.get_by_role("link", name="Vytlačiť so vzorom").is_visible()
        assert page.get_by_role("link", name="Stiahnuť PNG").get_attribute("href").endswith(".png")
        assert page.get_by_role("link", name="Stiahnuť farebnú verziu").get_attribute("href").endswith(
            "/color.png"
        )
        assert page.get_by_role("link", name="Stiahnuť PDF").get_attribute("href").endswith(".pdf")
        assert "Bleskový McQueen" in page.locator("#resultSummary").inner_text()
        assert "Mater / Burák" in page.locator("#resultSummary").inner_text()
        assert page.locator("#recentRail .recent-item").count() == 1
        assert not console_errors

        screenshot = tmp_path / "result.png"
        page.screenshot(path=str(screenshot), full_page=False)
        assert screenshot.is_file()
        browser.close()


def test_mobile_builder_has_no_horizontal_overflow(live_app: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_app, wait_until="networkidle")

        has_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        page.get_by_role("button", name="Autá").click()
        page.get_by_role("button", name="Bleskový McQueen").click()

        assert has_overflow is False
        assert page.get_by_role("button", name="Autá").get_attribute("aria-pressed") == "true"
        assert page.get_by_role("button", name="Bleskový McQueen").get_attribute("aria-pressed") == "true"
        browser.close()
