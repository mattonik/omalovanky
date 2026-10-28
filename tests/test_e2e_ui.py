from __future__ import annotations

import os
import json
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

        assert page.get_by_role("button", name="Na šírku").get_attribute("aria-pressed") == "true"
        assert page.get_by_role("button", name="Hrad").is_visible()
        page.get_by_role("button", name="Bleskový McQueen").click()
        page.get_by_role("button", name="Mater / Burák").click()
        page.get_by_role("button", name="Pretekajú").click()
        page.get_by_role("button", name="Na šírku").click()
        page.get_by_role("button", name="Farebný obrázok").click()
        page.get_by_role("button", name="Detailná").click()
        page.get_by_label("Vlastný nápad").fill("Bleskový McQueen a Mater pretekajú spolu")
        page.get_by_role("button", name="Vytvoriť omaľovánku").click()

        page.get_by_text("Omaľovánka #1").wait_for(timeout=5_000)
        page.get_by_role("button", name="Otvoriť").click()
        page.get_by_role("heading", name="Farebný obrázok je hotový!").wait_for(timeout=10_000)
        page.locator("#resultImage").wait_for(state="visible")
        page.locator("#resultImage").evaluate(
            "(image) => image.complete && image.naturalWidth > 0"
        )

        assert page.get_by_role("link", name="Stiahnuť farebné PDF").get_attribute("href").endswith(
            "/color.pdf"
        )
        with page.expect_download() as download_info:
            page.get_by_role("link", name="Stiahnuť farebné PDF").click()
        assert Path(download_info.value.path()).read_bytes().startswith(b"%PDF")
        assert page.locator('#renderModeControl [data-generation-mode="color_first"]').get_attribute(
            "aria-pressed"
        ) == "true"
        assert "Bleskový McQueen" in page.locator("#resultSummary").inner_text()
        assert "Mater / Burák" in page.locator("#resultSummary").inner_text()
        assert "detailná" in page.locator("#resultSummary").inner_text()
        assert page.locator("#recentRail .recent-item").count() == 1
        page.get_by_role("button", name="Nastavenia generovania").click()
        assert page.locator("#builderView").is_visible()
        assert page.locator("#generationSettings").evaluate("element => document.activeElement === element")
        assert page.get_by_role("button", name="Detailná").get_attribute("aria-pressed") == "true"
        assert page.locator("#recentSection").bounding_box()["y"] + page.locator("#recentSection").bounding_box()["height"] <= page.locator(".mode-switch").bounding_box()["y"]
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

        page.get_by_role("button", name="Pomoc").click()
        assert page.get_by_role("dialog", name="Pomoc").is_visible()
        page.get_by_role("button", name="Zavrieť").click()
        assert page.get_by_role("dialog", name="Pomoc").is_hidden()
        assert page.get_by_role("button", name="Nastavenia generovania").is_visible()
        assert page.locator(".world-card").count() == 0
        assert page.get_by_role("button", name="Bez pozadia").get_attribute("aria-pressed") == "true"
        has_overflow = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        page.get_by_role("button", name="Bleskový McQueen").click()

        assert has_overflow is False
        assert page.get_by_role("button", name="Bleskový McQueen").get_attribute("aria-pressed") == "true"
        browser.close()


def test_multi_page_coloring_download(live_app: str) -> None:
    import re
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(live_app, wait_until="networkidle")
        page.get_by_role("button", name="Princezná").click()
        page.get_by_label("Počet strán").fill("2")
        page.get_by_role("button", name="Vytvoriť omaľovánku").click()
        page.get_by_role("button", name="Otvoriť").click(timeout=15000)
        assert page.locator("#comicPages img").count() == 2
        with page.expect_download() as download_info:
            page.get_by_role("link", name="Stiahnuť PDF", exact=True).click()
        assert len(re.findall(rb"/Type\s*/Page\b", Path(download_info.value.path()).read_bytes())) == 2
        browser.close()


def test_generation_failure_returns_to_builder_without_unhandled_rejection(live_app: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 800})
        console_errors: list[str] = []
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        poll_count = 0
        submissions = []

        def mock_generation(route) -> None:
            nonlocal poll_count
            if route.request.method == "POST":
                submissions.append(route.request.post_data_json)
                route.fulfill(status=202, content_type="application/json", body='{"id": 99, "status": "queued"}')
                return
            poll_count += 1
            if poll_count == 1:
                route.fulfill(status=200, content_type="application/json", body='{"id": 99, "status": "queued"}')
            else:
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({"id": 99, "status": "failed", "error": "Toto zadanie generátor odmietol.", "request": submissions[0]}),
                )

        page.route("**/api/generations", mock_generation)
        page.route("**/api/generations/**", mock_generation)
        page.goto(live_app, wait_until="networkidle")
        page.get_by_role("button", name="Bleskový McQueen").click()
        page.get_by_role("button", name="Vytvoriť omaľovánku").click()

        page.locator("#formError").wait_for(state="visible", timeout=5000)
        assert "generátor odmietol" in page.locator("#formError").inner_text()
        assert page.locator("#loadingOverlay").is_hidden()
        assert page.locator("#builderView").is_visible()
        page.get_by_role("button", name="Skúsiť so všeobecnými postavami").click()
        assert submissions[-1]["generic_characters"] is True
        assert submissions[-1]["characters"] == ["lightning-mcqueen"]
        assert not any("Unhandled Promise" in error for error in console_errors)
        browser.close()


def test_job_recovers_from_temporary_poll_failure(live_app: str) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        polls = 0

        def mock_generation(route) -> None:
            nonlocal polls
            if route.request.method == "POST":
                route.fulfill(status=202, json={"id": 99, "status": "queued"})
                return
            polls += 1
            if polls == 1:
                route.fulfill(status=503, json={"detail": "unavailable"})
            else:
                route.fulfill(status=200, json={"id": 99, "status": "done"})

        page.route("**/api/generations", mock_generation)
        page.route("**/api/generations/**", mock_generation)
        page.goto(live_app, wait_until="networkidle")
        page.get_by_role("button", name="Vytvoriť omaľovánku").click()
        page.get_by_text("Čaká na spojenie").wait_for(timeout=5000)
        page.get_by_role("button", name="Otvoriť").wait_for(timeout=9000)
        browser.close()
