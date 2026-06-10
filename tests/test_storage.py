import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from private_pageindex.storage import (
    DocumentRecord,
    LocalStorage,
    NodeRecord,
    RetrievalStepRecord,
)


def fresh_runtime_dir() -> Path:
    path = Path("test_runtime") / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_initialize_creates_database_schema_idempotently():
    storage = LocalStorage(fresh_runtime_dir())

    storage.initialize()
    storage.initialize()

    with sqlite3.connect(storage.db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "documents",
        "nodes",
        "chat_sessions",
        "chats",
        "retrieval_steps",
    }.issubset(table_names)


def test_initialize_adds_progress_columns_to_existing_database():
    runtime_dir = fresh_runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    db_path = runtime_dir / "private_pageindex.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                page_count INTEGER,
                created_at TEXT NOT NULL,
                error TEXT
            )
            """
        )

    storage = LocalStorage(runtime_dir)
    storage.initialize()

    with sqlite3.connect(storage.db_path) as conn:
        column_names = {
            row[1]
            for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }

    assert {
        "progress_percent",
        "progress_stage",
        "started_at",
        "finished_at",
    }.issubset(column_names)


def test_document_node_chat_and_trace_records_round_trip():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()

    document = storage.create_document(
        filename="manual.pdf",
        status="processing",
        page_count=12,
    )
    storage.update_document_status(document.id, "completed")
    node = storage.insert_node(
        NodeRecord(
            doc_id=document.id,
            node_id="0001",
            title="Safety Requirements",
            start_page=2,
            end_page=5,
            summary="Safety section summary.",
            parent_node_id=None,
        )
    )
    session = storage.create_chat_session(document.id)
    chat = storage.insert_chat(
        doc_id=document.id,
        session_id=session.id,
        question="What are the safety requirements?",
        answer="Use protective equipment. [page 3]",
    )
    step = storage.insert_retrieval_step(
        RetrievalStepRecord(
            chat_id=chat.id,
            step_index=1,
            action="fetch_pages",
            node_id=node.node_id,
            pages="2-5",
            reason="The selected node covers safety requirements.",
        )
    )

    stored_document = storage.get_document(document.id)
    stored_nodes = storage.list_nodes(document.id)
    stored_steps = storage.list_retrieval_steps(chat.id)

    assert stored_document == DocumentRecord(
        id=document.id,
        filename="manual.pdf",
        status="completed",
        page_count=12,
        error=None,
        created_at=stored_document.created_at,
        progress_percent=100,
        progress_stage="completed",
        started_at=stored_document.started_at,
        finished_at=stored_document.finished_at,
    )
    assert stored_nodes == [node]
    assert stored_steps == [step]


def test_document_progress_round_trips_with_elapsed_seconds():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()
    document = storage.create_document(filename="manual.pdf", status="processing")

    storage.update_document_progress(
        document.id,
        progress_percent=45,
        progress_stage="building tree",
    )
    updated = storage.get_document(document.id)

    assert updated.progress_percent == 45
    assert updated.progress_stage == "building tree"
    assert updated.elapsed_seconds is not None
    assert updated.elapsed_seconds >= 0


def test_delete_document_removes_chats_retrieval_steps_and_files():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()
    document = storage.create_document(filename="manual.pdf", status="completed")
    storage.write_pages(document.id, [{"page_number": 1, "text": "Intro", "char_count": 5}])
    storage.write_tree(document.id, {"doc_id": document.id, "nodes": []})
    storage.upload_path(document.id).write_text("pdf bytes", encoding="utf-8")
    session = storage.create_chat_session(document.id)
    chat = storage.insert_chat(document.id, session.id, "Question?", "Answer.")
    storage.insert_retrieval_step(
        RetrievalStepRecord(
            chat_id=chat.id,
            step_index=0,
            action="inspect_tree",
            node_id=None,
            pages=None,
            reason="Start.",
        )
    )

    storage.delete_document(document.id)

    with pytest.raises(KeyError):
        storage.get_document(document.id)
    assert storage.list_chat_sessions(document.id) == []
    assert storage.list_chats(session.id) == []
    assert storage.count_retrieval_steps(chat.id) == 0
    assert not storage.upload_path(document.id).exists()
    assert not storage.document_dir(document.id).exists()


def test_cleanup_orphan_records_removes_stale_chats_and_traces():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()
    document = storage.create_document(filename="manual.pdf", status="completed")
    session = storage.create_chat_session(document.id)
    chat = storage.insert_chat(document.id, session.id, "Question?", "Answer.")
    storage.insert_retrieval_step(
        RetrievalStepRecord(
            chat_id=chat.id,
            step_index=0,
            action="fetch_pages",
            node_id=None,
            pages="1",
            reason="Old trace.",
        )
    )
    with sqlite3.connect(storage.db_path) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM documents WHERE id = ?", (document.id,))

    removed = storage.cleanup_orphan_records()

    assert removed["chat_sessions"] == 1
    assert removed["chats"] == 1
    assert removed["retrieval_steps"] == 1
    assert storage.list_retrieval_steps(chat.id) == []


def test_pages_and_tree_files_round_trip():
    storage = LocalStorage(fresh_runtime_dir())
    doc_id = "doc-123"
    pages = [
        {"page_number": 1, "text": "Introduction", "char_count": 12},
        {"page_number": 2, "text": "Details", "char_count": 7},
    ]
    tree = {
        "doc_id": doc_id,
        "nodes": [
            {
                "node_id": "0001",
                "title": "Introduction",
                "start_page": 1,
                "end_page": 2,
                "summary": "Intro summary.",
                "nodes": [],
            }
        ],
    }

    storage.write_pages(doc_id, pages)
    storage.write_tree(doc_id, tree)

    assert storage.read_pages(doc_id) == pages
    assert storage.read_tree(doc_id) == tree

    pages_path = storage.pages_path(doc_id)
    raw_lines = pages_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in raw_lines] == pages
    assert storage.tree_path(doc_id).exists()


def test_list_documents_returns_all_documents_ordered_newest_first():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()

    doc_a = storage.create_document(filename="alpha.pdf", status="completed")
    doc_b = storage.create_document(filename="beta.pdf", status="processing")
    doc_c = storage.create_document(filename="gamma.pdf", status="failed")

    documents = storage.list_documents()

    assert len(documents) == 3
    # Newest first (gamma was created last).
    assert documents[0].filename == "gamma.pdf"
    assert documents[1].filename == "beta.pdf"
    assert documents[2].filename == "alpha.pdf"
    assert all(isinstance(d, DocumentRecord) for d in documents)


def test_list_documents_returns_empty_list_when_no_documents():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()

    assert storage.list_documents() == []


def test_list_chats_with_limit_caps_results():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()
    document = storage.create_document(filename="manual.pdf", status="completed")
    session = storage.create_chat_session(document.id)

    for i in range(5):
        storage.insert_chat(document.id, session.id, f"Question {i}?", f"Answer {i}.")

    all_chats = storage.list_chats(session.id)
    limited = storage.list_chats(session.id, limit=3)

    assert len(all_chats) == 5
    assert len(limited) == 3


def test_recover_interrupted_documents_marks_processing_as_failed():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()

    doc_ok = storage.create_document(filename="done.pdf", status="completed")
    doc_stuck = storage.create_document(filename="stuck.pdf", status="processing")

    recovered = storage.recover_interrupted_documents()

    assert recovered == 1
    assert storage.get_document(doc_ok.id).status == "completed"

    stuck = storage.get_document(doc_stuck.id)
    assert stuck.status == "failed"
    assert "interrupted" in stuck.error.lower()
    assert stuck.progress_percent == 100
    assert stuck.progress_stage == "failed"


def test_recover_interrupted_documents_returns_zero_when_nothing_stuck():
    storage = LocalStorage(fresh_runtime_dir())
    storage.initialize()

    storage.create_document(filename="done.pdf", status="completed")

    assert storage.recover_interrupted_documents() == 0
