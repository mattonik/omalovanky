from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .schemas import Orientation

A4_300_DPI = {
    "portrait": (2480, 3508),
    "landscape": (3508, 2480),
}


@dataclass(frozen=True, slots=True)
class ProcessedFiles:
    png_path: Path
    pdf_path: Path


class ColoringProcessor:
    def process(
        self,
        *,
        generation_id: int,
        source_path: Path,
        output_dir: Path,
        orientation: Orientation,
    ) -> ProcessedFiles:
        output_dir.mkdir(parents=True, exist_ok=True)
        png_path = output_dir / f"{generation_id}.png"
        pdf_path = output_dir / f"{generation_id}.pdf"
        page_size = A4_300_DPI[orientation]
        margin = 140

        with Image.open(source_path) as source:
            grayscale = ImageOps.autocontrast(source.convert("L"))
            line_art = grayscale.point(lambda value: 255 if value > 210 else 0, mode="1")
            available = (page_size[0] - margin * 2, page_size[1] - margin * 2)
            line_art.thumbnail(available, Image.Resampling.LANCZOS)
            page = Image.new("1", page_size, 1)
            x = (page_size[0] - line_art.width) // 2
            y = (page_size[1] - line_art.height) // 2
            page.paste(line_art, (x, y))
            page.save(png_path, format="PNG", optimize=True, dpi=(300, 300))

        self._create_pdf(png_path=png_path, pdf_path=pdf_path, orientation=orientation)
        return ProcessedFiles(png_path=png_path, pdf_path=pdf_path)

    @staticmethod
    def _create_pdf(*, png_path: Path, pdf_path: Path, orientation: Orientation) -> None:
        page_size = A4 if orientation == "portrait" else landscape(A4)
        pdf = canvas.Canvas(str(pdf_path), pagesize=page_size)
        margin = 12 * 72 / 25.4
        width = page_size[0] - margin * 2
        height = page_size[1] - margin * 2
        pdf.drawImage(
            ImageReader(str(png_path)),
            margin,
            margin,
            width=width,
            height=height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        pdf.showPage()
        pdf.save()

