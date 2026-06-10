"""Tests for the CLI module."""

import uuid
from pathlib import Path

import fitz
import pytest

from private_pageindex.cli import main
from private_pageindex.ingest.pipeline import index_pdf
from private_pageindex.storage import LocalStorage


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


def test_cli_ingest_indexes_pdf(monkeypatch, capsys):
    test_dir = fresh_runtime_dir()
    monkeypatch.setenv("DATA_DIR", str(test_dir))
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "manual.pdf",
        ["1 Introduction\nOverview text."],
    )

    main(["ingest", str(pdf_path)])

    captured = capsys.readouterr()
    assert "Indexed" in captured.out
    assert "manual.pdf" in captured.out
    assert "doc_id" in captured.out


def test_cli_ingest_fails_for_missing_file(monkeypatch):
    test_dir = fresh_runtime_dir()
    monkeypatch.setenv("DATA_DIR", str(test_dir))

    with pytest.raises(SystemExit) as exc_info:
        main(["ingest", "nonexistent.pdf"])
    assert exc_info.value.code == 1


def test_cli_help_shows_usage(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "ingest" in captured.out
    assert "ask" in captured.out
    assert "serve" in captured.out
