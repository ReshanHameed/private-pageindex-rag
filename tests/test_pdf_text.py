import uuid
from pathlib import Path

import fitz
import pytest

from private_pageindex.ingest.pdf_text import PdfExtractionError, extract_pdf_text


def fresh_runtime_dir() -> Path:
    path = Path("test_runtime") / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=False)
    return path


def create_pdf(path: Path, page_texts: list[str]) -> Path:
    document = fitz.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def test_extract_pdf_text_returns_page_records_for_text_pdf():
    pdf_path = create_pdf(
        fresh_runtime_dir() / "manual.pdf",
        [
            "Introduction\nThis is a private text PDF.",
            "Safety Requirements\nWear protective equipment.",
        ],
    )

    pages = extract_pdf_text(pdf_path)

    assert [page.page_number for page in pages] == [1, 2]
    assert "Introduction" in pages[0].text
    assert "Safety Requirements" in pages[1].text
    assert pages[0].char_count == len(pages[0].text)
    assert pages[1].char_count == len(pages[1].text)


def test_extract_pdf_text_keeps_empty_pages_when_some_text_exists():
    pdf_path = create_pdf(
        fresh_runtime_dir() / "mixed.pdf",
        ["", "Only this page has selectable text."],
    )

    pages = extract_pdf_text(pdf_path)

    assert len(pages) == 2
    assert pages[0].text == ""
    assert pages[0].char_count == 0
    assert pages[1].text.startswith("Only this page")


def test_extract_pdf_text_fails_when_every_page_is_empty():
    pdf_path = create_pdf(fresh_runtime_dir() / "blank.pdf", ["", ""])

    with pytest.raises(PdfExtractionError, match="selectable text"):
        extract_pdf_text(pdf_path)


def test_extract_pdf_text_rejects_missing_or_non_pdf_files():
    runtime_dir = fresh_runtime_dir()
    text_path = runtime_dir / "notes.txt"
    text_path.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(PdfExtractionError, match="not found"):
        extract_pdf_text(runtime_dir / "missing.pdf")

    with pytest.raises(PdfExtractionError, match=".pdf"):
        extract_pdf_text(text_path)
