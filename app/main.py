from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import catalog_payload
from .config import Settings, settings
from .image_provider import ImageProvider, OpenAIImageProvider
from .prompting import build_image_prompt
from .schemas import GenerationRequest, GenerationStatus
from .storage import ActiveGenerationError, GenerationNotFoundError, Storage
from .worker import GenerationWorker

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@dataclass(slots=True)
class Services:
    storage: Storage
    worker: GenerationWorker


def create_app(
    app_settings: Settings | None = None,
    *,
    image_provider: ImageProvider | None = None,
    start_worker: bool = True,
) -> FastAPI:
    resolved_settings = app_settings or settings
    storage = Storage(resolved_settings.db_path)
    provider = image_provider or OpenAIImageProvider(resolved_settings.openai_api_key)
    worker = GenerationWorker(
        storage=storage,
        image_provider=provider,
        colorings_dir=resolved_settings.colorings_dir,
    )
    services = Services(storage=storage, worker=worker)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resolved_settings.db_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_settings.colorings_dir.mkdir(parents=True, exist_ok=True)
        storage.init_db()
        storage.recover_interrupted_generations()
        if start_worker:
            worker.start()
        try:
            yield
        finally:
            if start_worker:
                worker.stop()

    app = FastAPI(
        title="Čarovné omaľovánky",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.services = services
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

    @app.post(
        "/api/generations",
        response_model=GenerationStatus,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_generation(payload: GenerationRequest):
        try:
            item = storage.create_generation(payload, build_image_prompt(payload))
        except ActiveGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "generation_in_progress", "message": str(exc)},
            ) from exc
        worker.wake()
        return serialize_generation(item)

    @app.get("/api/generations/{generation_id}", response_model=GenerationStatus)
    def get_generation(generation_id: int):
        try:
            return serialize_generation(storage.get_generation(generation_id))
        except GenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/colorings", response_model=list[GenerationStatus])
    def list_colorings(limit: int = Query(default=20, ge=1, le=20)):
        return [serialize_generation(item) for item in storage.list_completed(limit)]

    @app.get("/colorings/{generation_id}.png")
    def download_png(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return serve_file(item["png_path"], "image/png", f"omalovanka-{generation_id}.png")

    @app.get("/colorings/{generation_id}/color.png")
    def download_color_png(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return serve_file(
            item["source_path"],
            "image/png",
            f"omalovanka-{generation_id}-farebna.png",
        )

    @app.get("/colorings/{generation_id}.pdf")
    def download_pdf(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return serve_file(item["pdf_path"], "application/pdf", f"omalovanka-{generation_id}.pdf")

    @app.get("/colorings/{generation_id}/print")
    def print_coloring(request: Request, generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return templates.TemplateResponse(
            request=request,
            name="print.html",
            context={
                "generation_id": generation_id,
                "orientation": item["request"]["orientation"],
                "mode": "plain",
                "lineart_url": f"/colorings/{generation_id}.png",
                "color_url": f"/colorings/{generation_id}/color.png",
            },
        )

    @app.get("/colorings/{generation_id}/print-pattern")
    def print_coloring_pattern(request: Request, generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return templates.TemplateResponse(
            request=request,
            name="print.html",
            context={
                "generation_id": generation_id,
                "orientation": item["request"]["orientation"],
                "mode": "pattern",
                "lineart_url": f"/colorings/{generation_id}.png",
                "color_url": f"/colorings/{generation_id}/color.png",
            },
        )

    @app.get("/healthz")
    def healthcheck():
        return {
            "status": "ok",
            "database_parent_ready": resolved_settings.db_path.parent.exists(),
            "colorings_dir_ready": resolved_settings.colorings_dir.exists(),
            "openai_api_key_present": resolved_settings.has_openai_api_key,
            "worker_alive": worker.is_alive() if start_worker else False,
        }

    return app


app = create_app()


def serialize_generation(item: dict) -> GenerationStatus:
    generation_id = int(item["id"])
    done = item["status"] == "done"
    return GenerationStatus(
        id=generation_id,
        status=item["status"],
        request=GenerationRequest.model_validate(item["request"]),
        error=item["error"],
        png_url=f"/colorings/{generation_id}.png" if done and item["png_path"] else None,
        pdf_url=f"/colorings/{generation_id}.pdf" if done and item["pdf_path"] else None,
        color_url=f"/colorings/{generation_id}/color.png" if done and item["source_path"] else None,
        print_url=f"/colorings/{generation_id}/print" if done and item["png_path"] else None,
        pattern_print_url=f"/colorings/{generation_id}/print-pattern"
        if done and item["png_path"] and item["source_path"]
        else None,
    )


def require_completed_generation(storage: Storage, generation_id: int) -> dict:
    try:
        item = storage.get_generation(generation_id)
    except GenerationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if item["status"] != "done":
        raise HTTPException(status_code=409, detail="Omaľovánka ešte nie je hotová.")
    return item


def serve_file(raw_path: str | None, media_type: str, filename: str) -> FileResponse:
    if not raw_path:
        raise HTTPException(status_code=404, detail="Výstupný súbor neexistuje.")
    path = Path(raw_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Výstupný súbor sa nenašiel na disku.")
    return FileResponse(path, media_type=media_type, filename=filename)
