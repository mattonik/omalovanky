from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_healthcheck_reports_ready_directories(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "state" / "app.db",
        colorings_dir=tmp_path / "state" / "colorings",
        openai_api_key_file=tmp_path / "missing-secret",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database_parent_ready": True,
        "colorings_dir_ready": True,
        "openai_secret_present": False,
    }


def test_homepage_is_slovak(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key_file=tmp_path / "secret",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'lang="sk"' in response.text
    assert "Čarovné omaľovánky" in response.text

