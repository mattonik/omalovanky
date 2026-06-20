from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_healthcheck_reports_ready_directories(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "state" / "app.db",
        colorings_dir=tmp_path / "state" / "colorings",
        openai_api_key=None,
    )

    with TestClient(create_app(settings, start_worker=False)) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database_parent_ready": True,
        "colorings_dir_ready": True,
        "openai_api_key_present": False,
        "worker_alive": False,
    }


def test_homepage_is_slovak(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "app.db",
        colorings_dir=tmp_path / "colorings",
        openai_api_key="test-api-key",
    )

    with TestClient(create_app(settings, start_worker=False)) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'lang="sk"' in response.text
    assert "Čarovné omaľovánky" in response.text


def test_settings_reads_openai_key_from_environment(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("COLORINGS_DIR", str(tmp_path / "colorings"))
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-test-from-env  ")

    settings = Settings.from_env()

    assert settings.openai_api_key == "  sk-test-from-env  "
    assert settings.has_openai_api_key is True
