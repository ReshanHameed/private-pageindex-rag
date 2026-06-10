from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be locally extracted as selectable text."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    char_count: int


def extract_pdf_text(pdf_path: str | Path) -> list[ExtractedPage]:
    """Extract selectable text from a local PDF using PyMuPDF."""

    path = Path(pdf_path)
    if not path.exists():
        raise PdfExtractionError(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise PdfExtractionError(f"Expected a .pdf file, got: {path}")

    try:
        document = fitz.open(path)
    except Exception as exc:
        raise PdfExtractionError(f"Failed to open PDF: {path}") from exc

    try:
        if document.needs_pass:
            raise PdfExtractionError(f"Encrypted PDF requires a password: {path}")

        pages: list[ExtractedPage] = []
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            pages.append(
                ExtractedPage(
                    page_number=index,
                    text=text,
                    char_count=len(text),
                )
            )
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError(f"Failed to extract PDF text: {path}") from exc
    finally:
        document.close()

    if not pages:
        raise PdfExtractionError(f"PDF has no pages: {path}")
    if all(page.char_count == 0 for page in pages):
        raise PdfExtractionError(
            "PDF has no selectable text. Scanned/OCR PDFs are not supported in v1."
        )

    return pages
