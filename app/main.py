from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import catalog_payload
from .config import Settings, settings

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app(app_settings: Settings | None = None) -> FastAPI:
    resolved_settings = app_settings or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_settings.colorings_dir.mkdir(parents=True, exist_ok=True)
        yield

    app = FastAPI(
        title="Čarovné omaľovánky",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    @app.get("/")
    def index(request: Request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"catalog": catalog_payload()},
        )

    @app.get("/api/catalog")
    def get_catalog():
        return catalog_payload()

    @app.get("/healthz")
    def healthcheck():
        return {
            "status": "ok",
            "database_parent_ready": resolved_settings.db_path.parent.exists(),
            "colorings_dir_ready": resolved_settings.colorings_dir.exists(),
            "openai_secret_present": resolved_settings.has_openai_secret,
        }

    return app


app = create_app()
