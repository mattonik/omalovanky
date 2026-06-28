from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .schemas import Orientation

A4_300_DPI = {
    "portrait": (2480, 3508),
    "landscape": (3508, 2480),
}
COMIC_PAGE_COUNT = 6


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
            available = (page_size[0] - margin * 2, page_size[1] - margin * 2)
            fitted = ImageOps.contain(grayscale, available, Image.Resampling.LANCZOS)
            line_art = fitted.point(lambda value: 255 if value > 210 else 0, mode="1")
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


@dataclass(frozen=True, slots=True)
class ComicFiles:
    color_pdf_path: Path
    line_art_pdf_path: Path


class ComicProcessor:
    def create_line_art_panel(self, *, source_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source_path) as source:
            grayscale = ImageOps.autocontrast(source.convert("L"))
            fitted = ImageOps.contain(grayscale, (1024, 1024), Image.Resampling.LANCZOS)
            line_art = fitted.point(lambda value: 255 if value > 210 else 0, mode="1")
            page = Image.new("1", (1024, 1024), 1)
            x = (page.width - line_art.width) // 2
            y = (page.height - line_art.height) // 2
            page.paste(line_art, (x, y))
            page.save(output_path, format="PNG", optimize=True, dpi=(300, 300))
        return output_path

    def create_mini_zine(
        self,
        *,
        comic_id: int,
        color_paths: list[Path],
        line_art_paths: list[Path],
        output_dir: Path,
    ) -> ComicFiles:
        self._validate_page_set(color_paths, "farebných strán")
        self._validate_page_set(line_art_paths, "omaľovánkových strán")
        output_dir.mkdir(parents=True, exist_ok=True)
        color_pdf_path = output_dir / f"comic-{comic_id}-color.pdf"
        line_art_pdf_path = output_dir / f"comic-{comic_id}-line-art.pdf"
        self._create_zine_pdf(paths=color_paths, pdf_path=color_pdf_path)
        self._create_zine_pdf(paths=line_art_paths, pdf_path=line_art_pdf_path)
        return ComicFiles(color_pdf_path=color_pdf_path, line_art_pdf_path=line_art_pdf_path)

    @staticmethod
    def _validate_page_set(paths: list[Path], label: str) -> None:
        if len(paths) != COMIC_PAGE_COUNT:
            raise ValueError(f"Komiks musí mať presne {COMIC_PAGE_COUNT} {label}.")

    @staticmethod
    def _create_zine_pdf(*, paths: list[Path], pdf_path: Path) -> None:
        page_size = landscape(A4)
        pdf = canvas.Canvas(str(pdf_path), pagesize=page_size)
        page_width, page_height = page_size
        cell_width = page_width / 4
        cell_height = page_height / 2
        slots = [
            (0, 1, "back", True),
            (1, 1, "6", True),
            (2, 1, "5", True),
            (3, 1, "cover", True),
            (0, 0, "1", False),
            (1, 0, "2", False),
            (2, 0, "3", False),
            (3, 0, "4", False),
        ]
        for col, row, slot, upside_down in slots:
            x = col * cell_width
            y = row * cell_height
            pdf.saveState()
            if upside_down:
                pdf.translate(x + cell_width, y + cell_height)
                pdf.rotate(180)
                local_x = local_y = 0
            else:
                pdf.translate(x, y)
                local_x = local_y = 0
            pdf.setStrokeColor(colors.lightgrey)
            pdf.rect(local_x + 3, local_y + 3, cell_width - 6, cell_height - 6, stroke=1, fill=0)
            margin = 12
            if slot == "cover":
                image_path = paths[0]
                pdf.drawImage(
                    ImageReader(str(image_path)),
                    margin,
                    margin + 18,
                    width=cell_width - margin * 2,
                    height=cell_height - margin * 2 - 18,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
                pdf.setFillColor(colors.black)
                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawCentredString(cell_width / 2, 12, "★")
            elif slot == "back":
                pdf.setFillColor(colors.black)
                pdf.setFont("Helvetica-Bold", 18)
                pdf.drawCentredString(cell_width / 2, cell_height / 2 + 10, "★  ♥  ★")
                pdf.setFont("Helvetica", 9)
                pdf.drawCentredString(cell_width / 2, cell_height / 2 - 10, " ")
            else:
                image_path = paths[int(slot) - 1]
                pdf.drawImage(
                    ImageReader(str(image_path)),
                    margin,
                    margin,
                    width=cell_width - margin * 2,
                    height=cell_height - margin * 2,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
            pdf.restoreState()
        pdf.showPage()
        pdf.save()
