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
    assert "dev" in captured.out


def test_build_dev_services_includes_backend_frontend_and_mcp():
    from private_pageindex.dev_runner import build_dev_services

    root = Path(__file__).resolve().parent.parent
    services = build_dev_services(
        project_root=root,
        python_executable="/usr/bin/python",
        host="127.0.0.1",
        port=8000,
        mcp_host="127.0.0.1",
        mcp_port=8765,
    )
    names = [service.name for service in services]
    assert names == ["backend", "frontend", "mcp-http"]
    assert services[0].command[1:4] == ["-m", "uvicorn", "private_pageindex.web.app:app"]
    assert "serve-mcp" in services[2].command
    assert "--http" in services[2].command
    assert services[2].command[-2:] == ["--port", "8765"]


def test_is_ollama_reachable_handles_connection_errors(monkeypatch):
    from private_pageindex.dev_runner import is_ollama_reachable

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            raise ConnectionError("offline")

    monkeypatch.setattr("private_pageindex.dev_runner.httpx.Client", FakeClient)
    assert is_ollama_reachable("http://localhost:11434") is False
