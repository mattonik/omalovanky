from __future__ import annotations

import threading

from .image_provider import ImageProvider
from .image_processing import ColoringProcessor
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
        poll_seconds: float = 0.25,
    ) -> None:
        self.storage = storage
        self.image_provider = image_provider
        self.colorings_dir = colorings_dir
        self.processor = processor or ColoringProcessor()
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
            return False

        generation_id = int(job["id"])
        try:
            request = GenerationRequest.model_validate(job["request"])
            generated = self.image_provider.generate(job["prompt"], request.orientation)
            self.colorings_dir.mkdir(parents=True, exist_ok=True)
            source_path = self.colorings_dir / f"{generation_id}-source.png"
            source_path.write_bytes(generated.content)
            processed = self.processor.process(
                generation_id=generation_id,
                source_path=source_path,
                output_dir=self.colorings_dir,
                orientation=request.orientation,
            )
            self.storage.mark_generation_done(
                generation_id,
                source_path=str(source_path),
                provider_request_id=generated.request_id,
                png_path=str(processed.png_path),
                pdf_path=str(processed.pdf_path),
            )
        except Exception as exc:  # noqa: BLE001
            self.storage.mark_generation_failed(generation_id, self._friendly_error(exc))
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
