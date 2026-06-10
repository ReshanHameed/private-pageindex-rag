import sqlite3
import uuid
from pathlib import Path

import fitz
import pytest

from private_pageindex.ingest.pipeline import IndexResult, PipelineError, index_pdf
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


def make_storage() -> LocalStorage:
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()
    return storage


def test_index_pdf_completes_successfully_with_text_pdf():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "manual.pdf",
        [
            "1 Introduction\nThis manual explains the machine.",
            "2 Safety Requirements\nWear protective equipment.",
            "2.1 Protective Equipment\nUse goggles and gloves.",
            "3 Maintenance\nClean the filters weekly.",
        ],
    )

    result = index_pdf(pdf_path, storage, max_pages_per_node=10)

    assert isinstance(result, IndexResult)
    assert result.filename == "manual.pdf"
    assert result.page_count == 4
    assert result.node_count >= 3  # At least the 3 top-level headings

    # Document record is completed.
    document = storage.get_document(result.doc_id)
    assert document.status == "completed"
    assert document.page_count == 4
    assert document.error is None

    # PDF was copied to uploads.
    assert storage.upload_path(result.doc_id).exists()

    # Pages JSONL was written.
    pages = storage.read_pages(result.doc_id)
    assert len(pages) == 4
    assert pages[0]["page_number"] == 1
    assert "Introduction" in pages[0]["text"]

    # Tree JSON was written.
    tree = storage.read_tree(result.doc_id)
    assert tree["doc_id"] == result.doc_id
    assert len(tree["nodes"]) >= 1

    # Node rows were inserted into SQLite.
    nodes = storage.list_nodes(result.doc_id)
    assert len(nodes) == result.node_count
    assert all(node.doc_id == result.doc_id for node in nodes)
    # All node_ids are zero-padded 4-digit strings.
    assert all(len(node.node_id) == 4 for node in nodes)


def test_index_pdf_uses_fallback_when_no_headings():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "plain.pdf",
        [
            "Some body text without a heading.",
            "More body text without a heading.",
            "Even more body text.",
        ],
    )

    result = index_pdf(pdf_path, storage, max_pages_per_node=2)

    assert result.page_count == 3
    assert result.node_count >= 2  # At least 2 page-range nodes

    nodes = storage.list_nodes(result.doc_id)
    assert len(nodes) == result.node_count


def test_index_pdf_marks_document_failed_on_extraction_error():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    # Create a blank PDF (no selectable text) — extraction should fail.
    pdf_path = create_pdf(source_dir / "blank.pdf", ["", ""])

    with pytest.raises(PipelineError, match="Indexing failed"):
        index_pdf(pdf_path, storage)

    # The document record should exist and be marked as failed.
    with sqlite3.connect(storage.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, status, error FROM documents LIMIT 1"
        ).fetchone()

    assert row is not None
    assert row["status"] == "failed"
    assert row["error"] is not None
    assert "selectable text" in row["error"].lower() or "PdfExtractionError" in row["error"]


def test_index_pdf_marks_document_failed_for_missing_pdf():
    storage = make_storage()
    missing_path = fresh_runtime_dir() / "does_not_exist.pdf"

    with pytest.raises(PipelineError, match="Indexing failed"):
        index_pdf(missing_path, storage)

    with sqlite3.connect(storage.db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status, error FROM documents LIMIT 1"
        ).fetchone()

    assert row["status"] == "failed"
    assert row["error"] is not None


def test_index_pdf_records_parent_node_ids_for_nested_headings():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "nested.pdf",
        [
            "1 Introduction\nOverview text.",
            "2 Safety\nSafety overview.",
            "2.1 Equipment\nGoggles and gloves.",
        ],
    )

    result = index_pdf(pdf_path, storage, max_pages_per_node=10)

    nodes = storage.list_nodes(result.doc_id)
    node_map = {node.node_id: node for node in nodes}

    # Find the child node (level 2 heading "Equipment")
    child_nodes = [node for node in nodes if node.parent_node_id is not None]
    assert len(child_nodes) >= 1

    child = child_nodes[0]
    parent = node_map[child.parent_node_id]
    assert "Safety" in parent.title or "Equipment" in child.title


def test_index_pdf_reports_progress_stages():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "progress.pdf",
        [
            "1 Introduction\nOverview text.",
            "2 Safety\nSafety text.",
        ],
    )
    stages: list[tuple[str, int]] = []

    result = index_pdf(
        pdf_path,
        storage,
        max_pages_per_node=10,
        progress_callback=lambda progress: stages.append(
            (progress.stage, progress.percent)
        ),
    )

    assert result.page_count == 2
    assert stages[0] == ("queued", 0)
    assert ("extracting text", 20) in stages
    assert ("building tree", 45) in stages
    assert ("writing artifacts", 70) in stages
    assert ("inserting nodes", 85) in stages
    assert stages[-1] == ("completed", 100)


def test_index_pdf_can_use_existing_processing_document():
    storage = make_storage()
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(source_dir / "existing.pdf", ["1 Intro\nText."])
    document = storage.create_document(filename="existing.pdf", status="processing")

    result = index_pdf(
        pdf_path,
        storage,
        existing_doc_id=document.id,
        max_pages_per_node=10,
    )

    assert result.doc_id == document.id
    assert storage.get_document(document.id).status == "completed"
    with sqlite3.connect(storage.db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    assert row[0] == 1
