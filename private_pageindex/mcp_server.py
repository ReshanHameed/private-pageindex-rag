"""MCP server exposing the private PageIndex RAG operations as tools.

External agents (Claude Desktop, Codex, Antigravity IDE, and others) can use
this server to ingest PDFs and query indexed documents. The server is a thin
wrapper over the existing local functions; it introduces no cloud dependencies
and keeps the project's privacy boundary intact:

- Document text stays under the local ``DATA_DIR``.
- Inference goes to the configured local Ollama endpoint only.

Transports:

- stdio (default): each agent launches the server locally over stdio.
- streamable HTTP (``--http``): one shared server instance that multiple
  agents connect to, bound to ``127.0.0.1`` by default and optionally guarded
  by a bearer token (``MCP_AUTH_TOKEN``).

Run it via::

    python -m private_pageindex.cli serve-mcp            # stdio
    python -m private_pageindex.cli serve-mcp --http     # shared HTTP
    private-pageindex-mcp                                 # console script (stdio)
"""

from __future__ import annotations

import argparse
import threading
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

from private_pageindex.config import get_settings
from private_pageindex.documents import delete_document_and_assets
from private_pageindex.ingest.pipeline import PipelineError, index_pdf
from private_pageindex.llm.ollama import OllamaClient
from private_pageindex.retrieval.answering import generate_answer, is_no_info_answer
from private_pageindex.retrieval.tree_search import search_tree, search_tree_broad
from private_pageindex.storage import LocalStorage, RetrievalStepRecord

mcp = FastMCP("private-pageindex-rag")

# Track background indexing threads so callers (and tests) can inspect them.
_INGEST_THREADS: dict[str, threading.Thread] = {}

_storage: LocalStorage | None = None


# ---------------------------------------------------------------------------
# Internal helpers (dependency seams for testing)
# ---------------------------------------------------------------------------

def _get_storage() -> LocalStorage:
    """Return a cached, initialized :class:`LocalStorage` for the tool process."""
    global _storage
    if _storage is None:
        settings = get_settings()
        storage = LocalStorage(settings.data_dir)
        storage.initialize()
        _storage = storage
    return _storage


def reset_state() -> None:
    """Reset cached module state. Intended for tests that swap ``DATA_DIR``."""
    global _storage
    _storage = None
    _INGEST_THREADS.clear()


def _inbox_dir() -> Path:
    settings = get_settings()
    inbox = Path(settings.inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    return inbox


def _make_llm_client(timeout: float = 300.0) -> OllamaClient:
    """Create the LLM client used for retrieval and answering (test seam)."""
    return OllamaClient(timeout=timeout)


def _make_indexing_llm_client() -> OllamaClient | None:
    """Create the LLM client used for background indexing enhancement.

    Returns ``None`` when a client cannot be constructed so indexing can
    proceed deterministically without LLM enhancement.
    """
    try:
        return OllamaClient(timeout=120)
    except Exception:
        return None


def _require_document(storage: LocalStorage, doc_id: str) -> Any:
    try:
        document = storage.get_document(doc_id)
    except KeyError as exc:
        raise ValueError(f"Document not found: {doc_id}") from exc
    return document


def _require_completed(storage: LocalStorage, doc_id: str) -> Any:
    document = _require_document(storage, doc_id)
    if document.status != "completed":
        raise ValueError(
            f"Document '{doc_id}' is not ready (status: {document.status}). "
            "Wait for indexing to complete before querying it."
        )
    return document


def _resolve_pdf_path(path: str | None, inbox_filename: str | None) -> Path:
    """Resolve the ingest source to a concrete local ``.pdf`` path."""
    if inbox_filename:
        inbox = _inbox_dir()
        candidate = (inbox / inbox_filename).resolve()
        # Prevent path traversal outside the inbox folder.
        if inbox.resolve() not in candidate.parents:
            raise ValueError("inbox_filename must be a file inside the inbox folder.")
    elif path:
        candidate = Path(path).expanduser().resolve()
    else:
        raise ValueError("Provide either 'path' or 'inbox_filename'.")

    if not candidate.exists() or not candidate.is_file():
        raise ValueError(f"PDF file not found: {candidate}")
    if candidate.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {candidate}")
    return candidate


def _run_indexing_job(path: str, doc_id: str, data_dir: str) -> None:
    """Background worker that indexes a PDF into an existing document record."""
    storage = LocalStorage(data_dir)
    storage.initialize()
    llm_client = _make_indexing_llm_client()
    try:
        index_pdf(Path(path), storage, llm_client=llm_client, existing_doc_id=doc_id)
    except PipelineError:
        # index_pdf already marked the document as 'failed'.
        pass
    except Exception as exc:  # pragma: no cover - defensive safety net
        try:
            storage.update_document_status(
                doc_id, "failed", error=f"{type(exc).__name__}: {exc}"
            )
        except Exception:
            pass
    finally:
        if llm_client is not None:
            llm_client.close()


def _persist_query(
    storage: LocalStorage,
    doc_id: str,
    session_id: str,
    question: str,
    answer: str,
    trace_steps: list[Any],
) -> str:
    """Persist a chat + retrieval trace so it appears in the web UI."""
    chat = storage.insert_chat(doc_id, session_id, question, answer)
    for idx, step in enumerate(trace_steps):
        storage.insert_retrieval_step(
            RetrievalStepRecord(
                chat_id=chat.id,
                step_index=idx,
                action=step.action,
                node_id=step.node_id,
                pages=step.pages,
                reason=step.reason,
            )
        )
    return chat.id


def _document_payload(document: Any) -> dict[str, Any]:
    return {
        "doc_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "page_count": document.page_count,
        "progress_percent": document.progress_percent,
        "progress_stage": document.progress_stage,
        "error": document.error,
        "created_at": document.created_at,
        "elapsed_seconds": document.elapsed_seconds,
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_documents() -> list[dict[str, Any]]:
    """List all indexed documents, newest first, with status and page counts."""
    storage = _get_storage()
    return [_document_payload(doc) for doc in storage.list_documents()]


@mcp.tool()
def get_document(doc_id: str) -> dict[str, Any]:
    """Get full metadata for one document (status, progress, page count, error)."""
    storage = _get_storage()
    document = _require_document(storage, doc_id)
    return _document_payload(document)


@mcp.tool()
def get_document_tree(doc_id: str) -> dict[str, Any]:
    """Get the PageIndex structure tree (sections, page ranges, summaries)."""
    storage = _get_storage()
    _require_completed(storage, doc_id)
    return storage.read_tree(doc_id)


@mcp.tool()
def list_inbox() -> dict[str, Any]:
    """List PDF files available in the local inbox folder for ingestion.

    Drop PDFs into this folder, then call ``ingest_pdf`` with the filename via
    the ``inbox_filename`` argument.
    """
    inbox = _inbox_dir()
    files = sorted(p.name for p in inbox.glob("*.pdf") if p.is_file())
    return {"inbox_dir": str(inbox), "files": files}


@mcp.tool()
def ingest_pdf(path: str | None = None, inbox_filename: str | None = None) -> dict[str, Any]:
    """Index a local PDF in the background and return its doc_id immediately.

    Provide exactly one source:
    - ``path``: an absolute or relative local filesystem path to a ``.pdf``.
    - ``inbox_filename``: the name of a ``.pdf`` inside the inbox folder
      (see ``list_inbox``), useful when the agent cannot pass absolute paths.

    Indexing runs asynchronously. Poll ``get_ingest_status`` with the returned
    ``doc_id`` until ``status`` is ``completed`` (or ``failed``).
    """
    storage = _get_storage()
    resolved = _resolve_pdf_path(path, inbox_filename)

    document = storage.create_document(filename=resolved.name, status="processing")
    doc_id = document.id

    thread = threading.Thread(
        target=_run_indexing_job,
        args=(str(resolved), doc_id, str(storage.data_dir)),
        daemon=True,
        name=f"ingest-{doc_id}",
    )
    _INGEST_THREADS[doc_id] = thread
    thread.start()

    return {
        "doc_id": doc_id,
        "filename": resolved.name,
        "status": "processing",
        "message": "Indexing started. Poll get_ingest_status for progress.",
    }


@mcp.tool()
def get_ingest_status(doc_id: str) -> dict[str, Any]:
    """Poll indexing progress for a document (percent, stage, status, error)."""
    storage = _get_storage()
    document = _require_document(storage, doc_id)
    return {
        "doc_id": document.id,
        "status": document.status,
        "progress_percent": document.progress_percent,
        "progress_stage": document.progress_stage,
        "page_count": document.page_count,
        "error": document.error,
        "elapsed_seconds": document.elapsed_seconds,
    }


@mcp.tool()
def retrieve_context(doc_id: str, query: str, max_pages: int | None = None) -> dict[str, Any]:
    """Retrieve the most relevant raw page text for a query (no LLM answer).

    Runs tree-guided retrieval and returns the raw text of the selected pages
    plus page-number citations, so the calling agent can reason over the source
    material itself. The query and its retrieval trace are persisted locally.
    """
    query = query.strip()
    if not query:
        raise ValueError("query is required.")

    storage = _get_storage()
    _require_completed(storage, doc_id)
    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    llm_client = _make_llm_client(timeout=120)
    try:
        retrieval = search_tree(query, tree, pages, llm_client)
    finally:
        llm_client.close()

    retrieved = retrieval.retrieved_pages
    if max_pages is not None and max_pages >= 0:
        retrieved = retrieved[:max_pages]

    citations = [p.get("page_number") for p in retrieved]
    context_pages = [
        {"page_number": p.get("page_number"), "text": p.get("text", "")}
        for p in retrieved
    ]

    session_id = storage.create_chat_session(doc_id).id
    marker = f"[context retrieval] {len(retrieved)} page(s): {citations}"
    chat_id = _persist_query(
        storage, doc_id, session_id, query, marker, retrieval.trace
    )

    return {
        "doc_id": doc_id,
        "query": query,
        "selected_node_ids": retrieval.selected_node_ids,
        "pages": context_pages,
        "citations": citations,
        "chat_id": chat_id,
        "session_id": session_id,
    }


@mcp.tool()
def ask(doc_id: str, question: str, session_id: str | None = None) -> dict[str, Any]:
    """Ask a question and get a grounded answer with [page N] citations.

    Runs tree-guided retrieval and local-Ollama answer generation, with a broad
    fallback when the first pass finds nothing. Pass a ``session_id`` to keep
    multi-turn context; omit it to start a new conversation thread. The chat and
    its retrieval trace are persisted locally.
    """
    question = question.strip()
    if not question:
        raise ValueError("question is required.")

    storage = _get_storage()
    _require_completed(storage, doc_id)
    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    if not session_id:
        session_id = storage.create_chat_session(doc_id).id

    llm_client = _make_llm_client(timeout=300)
    try:
        prior = storage.list_chats(session_id, limit=5)
        chat_history: list[dict[str, str]] = []
        for c in reversed(prior):
            chat_history.append({"role": "user", "content": c.question})
            chat_history.append({"role": "assistant", "content": c.answer})

        retrieval = search_tree(question, tree, pages, llm_client)
        answer_result = generate_answer(
            question, retrieval.retrieved_pages, llm_client, chat_history=chat_history
        )

        if is_no_info_answer(answer_result.answer):
            broad = search_tree_broad(question, tree, pages)
            if len(broad.retrieved_pages) > len(retrieval.retrieved_pages):
                answer_result = generate_answer(
                    question, broad.retrieved_pages, llm_client, chat_history=chat_history
                )
                retrieval = broad

        citations = [p.get("page_number") for p in retrieval.retrieved_pages]
        chat_id = _persist_query(
            storage,
            doc_id,
            session_id,
            question,
            answer_result.answer,
            retrieval.trace + [answer_result.trace_step],
        )
    finally:
        llm_client.close()

    return {
        "doc_id": doc_id,
        "question": question,
        "answer": answer_result.answer,
        "citations": citations,
        "selected_node_ids": retrieval.selected_node_ids,
        "chat_id": chat_id,
        "session_id": session_id,
    }


@mcp.tool()
def delete_document(doc_id: str) -> dict[str, str]:
    """Delete a document and all associated data (DB rows, PDF, pages, tree)."""
    storage = _get_storage()
    try:
        return delete_document_and_assets(doc_id, storage)
    except KeyError as exc:
        raise ValueError(f"Document not found: {doc_id}") from exc


@mcp.tool()
def ollama_status() -> dict[str, Any]:
    """Check whether the local Ollama server is reachable and list models."""
    llm_client = _make_llm_client(timeout=10)
    try:
        return llm_client.check_health()
    finally:
        llm_client.close()


# ---------------------------------------------------------------------------
# Transport wiring
# ---------------------------------------------------------------------------

def _wrap_with_auth(app: Any, token: str) -> Any:
    """Wrap an ASGI app with a minimal bearer-token gate for HTTP requests."""
    expected = f"Bearer {token}"

    async def middleware(scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http":
            headers = dict(scope.get("headers") or [])
            authorization = headers.get(b"authorization", b"").decode()
            if authorization != expected:
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await app(scope, receive, send)

    return middleware


def serve(*, http: bool = False, host: str | None = None, port: int | None = None) -> None:
    """Start the MCP server. Defaults to stdio; set ``http=True`` for HTTP."""
    settings = get_settings()
    _inbox_dir()  # ensure inbox exists so agents can drop files in

    if not http:
        mcp.run()  # stdio transport
        return

    bind_host = host or settings.mcp_http_host
    bind_port = port or settings.mcp_http_port

    app = mcp.streamable_http_app()
    token = (settings.mcp_auth_token or "").strip()
    if token:
        app = _wrap_with_auth(app, token)

    uvicorn.run(app, host=bind_host, port=bind_port)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="private-pageindex-mcp",
        description="MCP server for the private PageIndex RAG project.",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run as a shared streamable-HTTP server instead of stdio.",
    )
    parser.add_argument("--host", type=str, default=None, help="HTTP bind host.")
    parser.add_argument("--port", type=int, default=None, help="HTTP bind port.")
    args = parser.parse_args(argv)
    serve(http=args.http, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
