"""Tests for the MCP server tools.

These call the tool functions directly (FastMCP's ``@tool`` decorator returns
the original callable) against an isolated temp data directory with a fake LLM
client, so no local Ollama server is required.
"""

import json
import re
import uuid
from pathlib import Path

import fitz
import pytest

from private_pageindex import config, mcp_server
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


class FakeLLM:
    """Minimal stand-in for OllamaClient used by the retrieval/answer tools."""

    def __init__(self, node_ids=None, answer="The answer is on [page 1]."):
        self._node_ids = node_ids
        self._answer = answer
        self.closed = False

    def chat_json(self, system, user, schema_hint=None, history=None):
        ids = self._node_ids
        if ids is None:
            match = re.search(r"Available node_ids: (\[.*\])", user)
            ids = json.loads(match.group(1))[:1] if match else []
        return {"selected_node_ids": ids}

    def chat_text(self, system, user, history=None):
        return self._answer

    def check_health(self):
        return {
            "status": "connected",
            "model": "fake",
            "model_available": True,
            "models": ["fake"],
        }

    def close(self):
        self.closed = True


def _setup() -> tuple[LocalStorage, Path]:
    """Fresh storage injected into the MCP module for one test."""
    config.reset_settings()
    test_dir = fresh_runtime_dir()
    storage = LocalStorage(test_dir)
    storage.initialize()
    mcp_server.reset_state()
    mcp_server._storage = storage
    return storage, test_dir


def _index_sample_doc(storage: LocalStorage) -> str:
    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(
        source_dir / "manual.pdf",
        [
            "1 Introduction\nHello world overview text.",
            "2 Details\nMore detailed content here.",
        ],
    )
    result = index_pdf(pdf_path, storage, max_pages_per_node=10)
    return result.doc_id


def test_list_documents_empty():
    storage, _ = _setup()
    assert mcp_server.list_documents() == []


def test_list_and_get_document():
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)

    docs = mcp_server.list_documents()
    assert len(docs) == 1
    assert docs[0]["doc_id"] == doc_id
    assert docs[0]["status"] == "completed"

    detail = mcp_server.get_document(doc_id)
    assert detail["filename"] == "manual.pdf"
    assert detail["page_count"] == 2


def test_get_document_not_found_raises():
    _setup()
    with pytest.raises(ValueError):
        mcp_server.get_document("does-not-exist")


def test_get_document_tree_returns_nodes():
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)

    tree = mcp_server.get_document_tree(doc_id)
    assert "nodes" in tree
    assert len(tree["nodes"]) >= 1


def test_ingest_pdf_by_path_completes(monkeypatch):
    storage, test_dir = _setup()
    monkeypatch.setattr(mcp_server, "_make_indexing_llm_client", lambda: None)

    source_dir = fresh_runtime_dir()
    pdf_path = create_pdf(source_dir / "report.pdf", ["1 Intro\nSome text."])

    result = mcp_server.ingest_pdf(path=str(pdf_path))
    doc_id = result["doc_id"]
    assert result["status"] == "processing"

    mcp_server._INGEST_THREADS[doc_id].join(timeout=30)

    status = mcp_server.get_ingest_status(doc_id)
    assert status["status"] == "completed"
    assert status["progress_percent"] == 100


def test_ingest_pdf_requires_a_source():
    _setup()
    with pytest.raises(ValueError):
        mcp_server.ingest_pdf()


def test_list_inbox_and_ingest_by_inbox_filename(monkeypatch):
    storage, test_dir = _setup()
    inbox = test_dir / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("INBOX_DIR", str(inbox))
    config.reset_settings()
    monkeypatch.setattr(mcp_server, "_make_indexing_llm_client", lambda: None)

    create_pdf(inbox / "drop.pdf", ["1 Intro\nInbox text."])

    listing = mcp_server.list_inbox()
    assert "drop.pdf" in listing["files"]

    result = mcp_server.ingest_pdf(inbox_filename="drop.pdf")
    doc_id = result["doc_id"]
    mcp_server._INGEST_THREADS[doc_id].join(timeout=30)

    assert mcp_server.get_ingest_status(doc_id)["status"] == "completed"


def test_retrieve_context_returns_pages_and_persists(monkeypatch):
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)
    monkeypatch.setattr(mcp_server, "_make_llm_client", lambda timeout=300.0: FakeLLM())

    result = mcp_server.retrieve_context(doc_id, "What is the overview?")
    assert result["pages"], "expected at least one page of context"
    assert result["citations"]
    assert "text" in result["pages"][0]

    # Persisted as a chat + trace visible to the web UI.
    chats = storage.list_chats(result["session_id"])
    assert len(chats) == 1
    assert storage.count_retrieval_steps(result["chat_id"]) >= 1


def test_ask_returns_answer_and_persists(monkeypatch):
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)
    monkeypatch.setattr(
        mcp_server,
        "_make_llm_client",
        lambda timeout=300.0: FakeLLM(answer="The overview is here [page 1]."),
    )

    result = mcp_server.ask(doc_id, "What is the overview?")
    assert "[page 1]" in result["answer"]
    assert result["session_id"]
    assert result["chat_id"]

    chats = storage.list_chats(result["session_id"])
    assert len(chats) == 1
    assert chats[0].answer == "The overview is here [page 1]."


def test_ask_reuses_session(monkeypatch):
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)
    monkeypatch.setattr(mcp_server, "_make_llm_client", lambda timeout=300.0: FakeLLM())

    first = mcp_server.ask(doc_id, "First question?")
    session_id = first["session_id"]
    mcp_server.ask(doc_id, "Second question?", session_id=session_id)

    chats = storage.list_chats(session_id)
    assert len(chats) == 2


def test_delete_document():
    storage, _ = _setup()
    doc_id = _index_sample_doc(storage)

    result = mcp_server.delete_document(doc_id)
    assert result["status"] == "success"
    assert mcp_server.list_documents() == []


def test_delete_document_not_found_raises():
    _setup()
    with pytest.raises(ValueError):
        mcp_server.delete_document("missing")


def test_ollama_status(monkeypatch):
    _setup()
    monkeypatch.setattr(mcp_server, "_make_llm_client", lambda timeout=300.0: FakeLLM())
    status = mcp_server.ollama_status()
    assert status["status"] == "connected"
