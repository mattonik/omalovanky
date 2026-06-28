from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as RoutePath, Query, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import catalog_payload
from .config import Settings, settings
from .image_provider import ImageProvider, OpenAIImageProvider
from .image_processing import COMIC_PAGE_COUNT
from .prompting import build_color_preview_prompt, build_comic_page_prompts, build_image_prompt
from .schemas import ComicPageStatus, ComicRequest, ComicStatus, GenerationRequest, GenerationStatus
from .storage import ActiveGenerationError, ComicNotFoundError, GenerationNotFoundError, Storage
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
        prompt = (
            build_color_preview_prompt(payload)
            if payload.generation_mode == "color_first"
            else build_image_prompt(payload)
        )
        try:
            item = storage.create_generation(payload, prompt)
        except ActiveGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "generation_in_progress", "message": str(exc)},
            ) from exc
        worker.wake()
        return serialize_generation(item)

    @app.post(
        "/api/comics",
        response_model=ComicStatus,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_comic(payload: ComicRequest):
        prompts = build_comic_page_prompts(payload)
        try:
            item = storage.create_comic(payload, prompts)
        except ActiveGenerationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "generation_in_progress", "message": str(exc)},
            ) from exc
        worker.wake()
        return serialize_comic(item)

    @app.get("/api/generations/{generation_id}", response_model=GenerationStatus)
    def get_generation(generation_id: int):
        try:
            return serialize_generation(storage.get_generation(generation_id))
        except GenerationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/comics/{comic_id}", response_model=ComicStatus)
    def get_comic(comic_id: int):
        try:
            return serialize_comic(storage.get_comic(comic_id))
        except ComicNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/colorings", response_model=list[GenerationStatus])
    def list_colorings(limit: int = Query(default=20, ge=1, le=20)):
        return [serialize_generation(item) for item in storage.list_completed(limit)]

    @app.get("/api/comics", response_model=list[ComicStatus])
    def list_comics(limit: int = Query(default=20, ge=1, le=20)):
        return [serialize_comic(item) for item in storage.list_completed_comics(limit)]

    @app.get("/colorings/{generation_id}.png")
    def download_png(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return serve_file(item["png_path"], "image/png", f"omalovanka-{generation_id}.png")

    @app.get("/colorings/{generation_id}/color.png")
    def download_color_png(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        if not item["color_path"]:
            raise HTTPException(status_code=404, detail="Farebná verzia nie je k dispozícii.")
        return serve_file(
            item["color_path"],
            "image/png",
            f"omalovanka-{generation_id}-farebna.png",
        )

    @app.get("/colorings/{generation_id}.pdf")
    def download_pdf(generation_id: int):
        item = require_completed_generation(storage, generation_id)
        return serve_file(item["pdf_path"], "application/pdf", f"omalovanka-{generation_id}.pdf")

    @app.get("/comics/{comic_id}/color.pdf")
    def download_comic_color_pdf(comic_id: int):
        item = require_completed_comic(storage, comic_id)
        return serve_file(item["color_pdf_path"], "application/pdf", f"komiks-{comic_id}-farebny.pdf")

    @app.get("/comics/{comic_id}/line-art.pdf")
    def download_comic_line_art_pdf(comic_id: int):
        item = require_completed_comic(storage, comic_id)
        return serve_file(
            item["line_art_pdf_path"],
            "application/pdf",
            f"komiks-{comic_id}-omalovankovy.pdf",
        )

    @app.get("/comics/{comic_id}/pages/{page_number}/color.png")
    def download_comic_page_color(
        comic_id: int,
        page_number: int = RoutePath(ge=1, le=COMIC_PAGE_COUNT),
    ):
        item = require_completed_comic(storage, comic_id)
        page = require_comic_page(item, page_number)
        return serve_file(page["color_path"], "image/png", f"komiks-{comic_id}-{page_number}-farebny.png")

    @app.get("/comics/{comic_id}/pages/{page_number}/line-art.png")
    def download_comic_page_line_art(
        comic_id: int,
        page_number: int = RoutePath(ge=1, le=COMIC_PAGE_COUNT),
    ):
        item = require_completed_comic(storage, comic_id)
        page = require_comic_page(item, page_number)
        return serve_file(
            page["line_art_path"],
            "image/png",
            f"komiks-{comic_id}-{page_number}-omalovankovy.png",
        )

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
        if not item["color_path"]:
            raise HTTPException(status_code=404, detail="Farebný vzor nie je k dispozícii.")
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
        color_url=f"/colorings/{generation_id}/color.png" if done and item["color_path"] else None,
        print_url=f"/colorings/{generation_id}/print" if done and item["png_path"] else None,
        pattern_print_url=f"/colorings/{generation_id}/print-pattern"
        if done and item["png_path"] and item["color_path"]
        else None,
    )


def serialize_comic(item: dict) -> ComicStatus:
    comic_id = int(item["id"])
    done = item["status"] == "done"
    pages = []
    for page in item["pages"]:
        page_number = int(page["page_number"])
        pages.append(
            ComicPageStatus(
                page_number=page_number,
                color_url=f"/comics/{comic_id}/pages/{page_number}/color.png"
                if done and page["color_path"]
                else None,
                line_art_url=f"/comics/{comic_id}/pages/{page_number}/line-art.png"
                if done and page["line_art_path"]
                else None,
            )
        )
    return ComicStatus(
        id=comic_id,
        status=item["status"],
        request=ComicRequest.model_validate(item["request"]),
        error=item["error"],
        pages=pages,
        color_pdf_url=f"/comics/{comic_id}/color.pdf" if done and item["color_pdf_path"] else None,
        line_art_pdf_url=f"/comics/{comic_id}/line-art.pdf"
        if done and item["line_art_pdf_path"]
        else None,
        print_url=f"/comics/{comic_id}/line-art.pdf" if done and item["line_art_pdf_path"] else None,
    )


def require_completed_generation(storage: Storage, generation_id: int) -> dict:
    try:
        item = storage.get_generation(generation_id)
    except GenerationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if item["status"] != "done":
        raise HTTPException(status_code=409, detail="Omaľovánka ešte nie je hotová.")
    return item


def require_completed_comic(storage: Storage, comic_id: int) -> dict:
    try:
        item = storage.get_comic(comic_id)
    except ComicNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if item["status"] != "done":
        raise HTTPException(status_code=409, detail="Komiks ešte nie je hotový.")
    if not item["color_pdf_path"] or not item["line_art_pdf_path"]:
        raise HTTPException(status_code=409, detail="Komiks nemá kompletné PDF výstupy.")
    complete_pages = [
        page
        for page in item["pages"]
        if page["color_path"] and page["line_art_path"]
    ]
    if len(complete_pages) != COMIC_PAGE_COUNT:
        raise HTTPException(status_code=409, detail="Komiks nemá kompletné stránky.")
    return item


def require_comic_page(item: dict, page_number: int) -> dict:
    for page in item["pages"]:
        if int(page["page_number"]) == page_number:
            return page
    raise HTTPException(status_code=404, detail="Strana komiksu neexistuje.")


def serve_file(raw_path: str | None, media_type: str, filename: str) -> FileResponse:
    if not raw_path:
        raise HTTPException(status_code=404, detail="Výstupný súbor neexistuje.")
    path = Path(raw_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Výstupný súbor sa nenašiel na disku.")
    return FileResponse(path, media_type=media_type, filename=filename)
