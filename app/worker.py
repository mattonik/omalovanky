from __future__ import annotations

import threading
from pathlib import Path

from .image_provider import ImageProvider
from .image_processing import ColoringProcessor, ComicProcessor
from .prompting import build_color_preview_prompt, build_image_prompt, build_line_art_edit_prompt
from .schemas import GenerationRequest
from .storage import Storage


class GenerationWorker:
    def __init__(
        self,
        *,
        storage: Storage,
        image_provider: ImageProvider,
        colorings_dir: Path,
        processor: ColoringProcessor | None = None,
        comic_processor: ComicProcessor | None = None,
        poll_seconds: float = 0.25,
    ) -> None:
        self.storage = storage
        self.image_provider = image_provider
        self.colorings_dir = colorings_dir
        self.processor = processor or ColoringProcessor()
        self.comic_processor = comic_processor or ComicProcessor()
        self.poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="coloring-generation-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def wake(self) -> None:
        self._wake_event.set()

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def process_one(self) -> bool:
        job = self.storage.claim_next_generation()
        if job is None:
            comic = self.storage.claim_next_comic()
            if comic is None:
                return False
            return self._process_comic(comic)

        generation_id = int(job["id"])
        try:
            request = GenerationRequest.model_validate(job["request"])
            source_prompt = job["prompt"] or (
                build_color_preview_prompt(request)
                if request.generation_mode == "color_first"
                else build_image_prompt(request)
            )
            self.colorings_dir.mkdir(parents=True, exist_ok=True)
            source_path = self.colorings_dir / f"{generation_id}-source.png"
            color_path = self.colorings_dir / f"{generation_id}-color.png"

            generated = self.image_provider.generate(source_prompt, request.orientation)
            source_path.write_bytes(generated.content)
            provider_request_id = generated.request_id
            if request.generation_mode == "color_first":
                color_path.write_bytes(generated.content)
            else:
                color_path = None

            try:
                processed = self.processor.process(
                    generation_id=generation_id,
                    source_path=source_path,
                    output_dir=self.colorings_dir,
                    orientation=request.orientation,
                )
            except Exception:
                edited_source_path = self.colorings_dir / f"{generation_id}-fallback-lineart.png"
                edited = self.image_provider.edit(
                    source_path=source_path,
                    prompt=build_line_art_edit_prompt(request),
                    orientation=request.orientation,
                )
                edited_source_path.write_bytes(edited.content)
                provider_request_id = edited.request_id or provider_request_id
                processed = self.processor.process(
                    generation_id=generation_id,
                    source_path=edited_source_path,
                    output_dir=self.colorings_dir,
                    orientation=request.orientation,
                )
            self.storage.mark_generation_done(
                generation_id,
                source_path=str(source_path),
                color_path=str(color_path) if color_path is not None else None,
                provider_request_id=provider_request_id,
                png_path=str(processed.png_path),
                pdf_path=str(processed.pdf_path),
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.mark_generation_failed(generation_id, self._friendly_error(exc))
        return True

    def _process_comic(self, comic: dict) -> bool:
        comic_id = int(comic["id"])
        try:
            comic_dir = self.colorings_dir / f"comic-{comic_id}"
            comic_dir.mkdir(parents=True, exist_ok=True)
            color_paths: list[Path] = []
            line_art_paths: list[Path] = []
            for page in comic["pages"]:
                page_number = int(page["page_number"])
                color_path = comic_dir / f"page-{page_number}-color.png"
                line_art_path = comic_dir / f"page-{page_number}-line-art.png"
                if not color_path.is_file():
                    generated = self.image_provider.generate(page["prompt"], "landscape")
                    color_path.write_bytes(generated.content)
                    provider_request_id = generated.request_id
                else:
                    provider_request_id = page.get("provider_request_id")
                if not line_art_path.is_file():
                    self.comic_processor.create_line_art_panel(
                        source_path=color_path,
                        output_path=line_art_path,
                    )
                self.storage.mark_comic_page_done(
                    comic_id,
                    page_number,
                    provider_request_id=provider_request_id,
                    color_path=str(color_path),
                    line_art_path=str(line_art_path),
                )
                color_paths.append(color_path)
                line_art_paths.append(line_art_path)

            files = self.comic_processor.create_mini_zine(
                comic_id=comic_id,
                color_paths=color_paths,
                line_art_paths=line_art_paths,
                output_dir=self.colorings_dir,
            )
            self.storage.mark_comic_done(
                comic_id,
                color_pdf_path=str(files.color_pdf_path),
                line_art_pdf_path=str(files.line_art_pdf_path),
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.mark_comic_failed(comic_id, self._friendly_error(exc))
        return True

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = self.process_one()
            if processed:
                continue
            self._wake_event.wait(self.poll_seconds)
            self._wake_event.clear()

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        code = getattr(error, "code", None)
        if code == "moderation_blocked":
            return "Toto zadanie generátor odmietol. Skúste scénu opísať jednoduchšie."
        status_code = getattr(error, "status_code", None)
        if status_code == 429:
            return "OpenAI limit je momentálne vyčerpaný. Skúste to neskôr."
        return str(error) or "Generovanie zlyhalo bez bližšieho popisu."
