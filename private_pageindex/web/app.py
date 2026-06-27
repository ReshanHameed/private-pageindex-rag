"""Local web application for private PageIndex RAG."""

from __future__ import annotations



import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from private_pageindex.config import get_settings
from private_pageindex.ingest.pipeline import PipelineError, index_pdf
from private_pageindex.llm.ollama import AsyncOllamaClient, OllamaClient, OllamaError
from private_pageindex.retrieval.answering import (
    generate_answer_async,
    generate_answer_stream,
    is_no_info_answer,
)
from private_pageindex.retrieval.tree_search import search_tree_async, search_tree_broad_async
from private_pageindex.storage import LocalStorage

settings = get_settings()
storage = LocalStorage(settings.data_dir)
storage.initialize()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown lifecycle for the application.

    On startup: recover any documents stuck in 'processing' from a
    previous unclean shutdown.
    """
    storage.recover_interrupted_documents()
    storage.cleanup_orphan_records()
    yield


app = FastAPI(title="Private PageIndex RAG", version="0.1.0", lifespan=lifespan)

# Static files and templates
_web_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=_web_dir / "static"), name="static")
templates = Jinja2Templates(directory=_web_dir / "templates")




def _normalize_model(model: str | None) -> str | None:
    model_name = (model or "").strip()
    return model_name or None


def _document_status_payload(doc_id: str) -> dict[str, Any]:
    document = storage.get_document(doc_id)
    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "page_count": document.page_count,
        "error": document.error,
        "created_at": document.created_at,
        "progress_percent": document.progress_percent,
        "progress_stage": document.progress_stage,
        "elapsed_seconds": document.elapsed_seconds,
    }


def _run_indexing_job(doc_id: str, model: str | None) -> None:
    """Run indexing after the upload response has been returned."""
    llm_client = None
    try:
        llm_client = OllamaClient(timeout=120, model=model)
        index_pdf(
            storage.upload_path(doc_id),
            storage,
            llm_client=llm_client,
            existing_doc_id=doc_id,
        )
    except PipelineError:
        pass
    except Exception as exc:
        storage.update_document_status(
            doc_id,
            "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if llm_client:
            try:
                llm_client.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Redirect legacy favicon requests to the SVG icon."""
    return RedirectResponse(url="/static/favicon.svg", status_code=301)


@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    """Document list and upload page."""
    documents = storage.list_documents()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"documents": documents},
    )


@app.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = Form(""),
):
    """Upload and index a PDF."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    selected_model = _normalize_model(model)
    document = storage.create_document(filename=file.filename, status="processing")
    upload_path = storage.upload_path(document.id)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    storage.update_document_progress(
        document.id,
        progress_percent=5,
        progress_stage="saving upload",
    )
    try:
        with upload_path.open("wb") as out:
            content = await file.read()
            out.write(content)
    except Exception as exc:
        storage.update_document_status(
            document.id,
            "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        return RedirectResponse(url="/", status_code=303)

    background_tasks.add_task(_run_indexing_job, document.id, selected_model)
    return RedirectResponse(url="/", status_code=303)


@app.post("/documents/{doc_id}/delete")
def delete_document(doc_id: str):
    """Delete a document and all associated data (DB + files)."""
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage.delete_document(doc_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/documents/{doc_id}", response_class=HTMLResponse)
def document_detail(request: Request, doc_id: str):
    """Document detail page with tree viewer and chat."""
    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    tree: dict[str, Any] = {}
    pages: list[dict[str, Any]] = []
    chats: list[dict[str, Any]] = []

    if document.status == "completed":
        try:
            tree = storage.read_tree(doc_id)
        except Exception:
            tree = {"nodes": []}
        try:
            pages = storage.read_pages(doc_id)
        except Exception:
            pages = []

        # Load chat history for the most recent session
        sessions = storage.list_chat_sessions(doc_id)
        if not sessions:
            session = storage.create_chat_session(doc_id)
            sessions = [session]
        chats = storage.list_chats(sessions[0].id, limit=20)

    return templates.TemplateResponse(
        request=request,
        name="document.html",
        context={
            "document": document,
            "tree": tree,
            "page_count": len(pages),
            "chats": chats,
        },
    )


@app.post("/documents/{doc_id}/ask", response_class=HTMLResponse)
async def ask_question(request: Request, doc_id: str):
    """Ask a question about a document."""
    form = await request.form()
    question = str(form.get("question", "")).strip()
    selected_model = _normalize_model(str(form.get("model", "")))
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    llm_client = AsyncOllamaClient(timeout=600, model=selected_model)
    try:
        # Tree search (async — does not block the event loop)
        retrieval = await search_tree_async(question, tree, pages, llm_client)

        # Answer generation (async)
        answer_result = await generate_answer_async(question, retrieval.retrieved_pages, llm_client)

        # Self-check & Retry: If LLM answers "no information", broaden search to all root sections
        if is_no_info_answer(answer_result.answer):
            broad_retrieval = await search_tree_broad_async(question, tree, pages)
            if len(broad_retrieval.retrieved_pages) > len(retrieval.retrieved_pages):
                retry_answer = await generate_answer_async(question, broad_retrieval.retrieved_pages, llm_client)
                answer_result = retry_answer
                retrieval = broad_retrieval

        session_id = str(form.get("session_id", "")).strip()
        if not session_id:
            session = storage.create_chat_session(doc_id)
            session_id = session.id

        # Store chat
        chat = storage.insert_chat(doc_id, session_id, question, answer_result.answer)

        # Store retrieval trace
        all_trace_steps = retrieval.trace + [answer_result.trace_step]
        for idx, step in enumerate(all_trace_steps):
            from private_pageindex.storage import RetrievalStepRecord
            storage.insert_retrieval_step(RetrievalStepRecord(
                chat_id=chat.id,
                step_index=idx,
                action=step.action,
                node_id=step.node_id,
                pages=step.pages,
                reason=step.reason,
            ))
    finally:
        await llm_client.close()

    return RedirectResponse(url=f"/documents/{doc_id}", status_code=303)


@app.get("/documents/{doc_id}/chats/{chat_id}/trace", response_class=HTMLResponse)
def chat_trace(request: Request, doc_id: str, chat_id: str):
    """Retrieval trace for a specific chat."""
    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    steps = storage.list_retrieval_steps(chat_id)
    return templates.TemplateResponse(
        request=request,
        name="trace.html",
        context={"document": document, "chat_id": chat_id, "steps": steps},
    )


@app.get("/api/ollama-status", response_class=JSONResponse)
async def ollama_status():
    """Check whether the local Ollama server is reachable.

    Uses the lightweight ``/api/tags`` endpoint (no inference) so this
    responds instantly even when the model is not loaded yet.
    """
    try:
        client = AsyncOllamaClient(timeout=5)
        try:
            health = await client.check_health()
            return health
        finally:
            await client.close()
    except Exception:
        return {"status": "unreachable", "detail": "Unable to check Ollama status"}


@app.get("/api/ollama-models", response_class=JSONResponse)
async def ollama_models():
    """Return available local Ollama model names."""
    try:
        client = AsyncOllamaClient(timeout=5)
        try:
            health = await client.check_health()
        finally:
            await client.close()
    except Exception:
        return {
            "status": "unreachable",
            "default_model": settings.ollama_model,
            "models": [],
            "detail": "Unable to retrieve Ollama models",
        }
    return {
        "status": health.get("status", "error"),
        "default_model": settings.ollama_model,
        "models": health.get("models", []),
    }


@app.get("/api/documents/{doc_id}/status", response_class=JSONResponse)
def document_status(doc_id: str):
    """Return progress and elapsed indexing time for one document."""
    try:
        return _document_status_payload(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")


@app.get("/api/documents", response_class=JSONResponse)
def api_list_documents():
    """Return all documents ordered by creation time (newest first)."""
    documents = storage.list_documents()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "page_count": doc.page_count,
            "error": doc.error,
            "created_at": doc.created_at,
            "progress_percent": doc.progress_percent,
            "progress_stage": doc.progress_stage,
            "elapsed_seconds": doc.elapsed_seconds,
        }
        for doc in documents
    ]


@app.get("/api/documents/{doc_id}", response_class=JSONResponse)
def api_get_document(doc_id: str):
    """Return details for a specific document."""
    try:
        return _document_status_payload(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")


@app.get("/api/documents/{doc_id}/tree", response_class=JSONResponse)
def api_get_document_tree(doc_id: str):
    """Return the structured tree JSON for a specific document."""
    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    if document.status != "completed":
        raise HTTPException(status_code=400, detail="Document indexing is not completed.")

    try:
        tree = storage.read_tree(doc_id)
        return tree
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read tree: {exc}")


@app.get("/api/documents/{doc_id}/sessions", response_class=JSONResponse)
def api_get_document_sessions(doc_id: str):
    """Return all chat sessions for a document."""
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    sessions = storage.list_chat_sessions(doc_id)
    
    # Filter out empty sessions
    valid_sessions = []
    for s in sessions:
        if storage.list_chats(s.id, limit=1):
            valid_sessions.append(s)

    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in valid_sessions
    ]


@app.delete("/api/documents/{doc_id}/sessions/{session_id}", response_class=JSONResponse)
def api_delete_chat_session(doc_id: str, session_id: str):
    """Delete a chat session and all its messages."""
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    success = storage.delete_chat_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found.")
        
    return {"status": "success"}


@app.get("/api/documents/{doc_id}/chats/{chat_id}", response_class=JSONResponse)
def api_get_chat(doc_id: str, chat_id: str):
    """Return a specific chat and its trace."""
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        chat = storage.get_chat(chat_id)
        if chat.doc_id != doc_id:
            raise KeyError("Chat doc_id mismatch")
    except KeyError:
        raise HTTPException(status_code=404, detail="Chat not found.")

    steps = storage.list_retrieval_steps(chat_id)
    return {
        "id": chat.id,
        "session_id": chat.session_id,
        "question": chat.question,
        "answer": chat.answer,
        "created_at": chat.created_at,
        "trace_steps": [
            {
                "step_index": s.step_index,
                "action": s.action,
                "node_id": s.node_id,
                "pages": s.pages,
                "reason": s.reason,
                "created_at": chat.created_at,
            }
            for s in steps
        ]
    }

@app.get("/api/documents/{doc_id}/sessions/{session_id}/chats", response_class=JSONResponse)
def api_get_session_chats(doc_id: str, session_id: str):
    """Return chat history and retrieval traces for a specific session."""
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    chats = storage.list_chats(session_id, limit=50)
    
    # Enrich with steps
    result = []
    for chat in chats:
        steps = storage.list_retrieval_steps(chat.id)
        result.append({
            "id": chat.id,
            "question": chat.question,
            "answer": chat.answer,
            "created_at": chat.created_at,
            "trace_steps": [
                {
                    "step_index": s.step_index,
                    "action": s.action,
                    "node_id": s.node_id,
                    "pages": s.pages,
                    "reason": s.reason,
                    "created_at": chat.created_at,
                }
                for s in steps
            ]
        })
    return result


@app.post("/api/upload", response_class=JSONResponse)
async def api_upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model: str = Form(""),
):
    """Upload and index a PDF, returning the document record as JSON."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are accepted.")

    selected_model = _normalize_model(model)
    document = storage.create_document(filename=file.filename, status="processing")
    upload_path = storage.upload_path(document.id)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    storage.update_document_progress(
        document.id,
        progress_percent=5,
        progress_stage="saving upload",
    )
    try:
        with upload_path.open("wb") as out:
            content = await file.read()
            out.write(content)
    except Exception as exc:
        storage.update_document_status(
            document.id,
            "failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        return JSONResponse(
            status_code=500,
            content=_document_status_payload(document.id),
        )

    background_tasks.add_task(_run_indexing_job, document.id, selected_model)
    return _document_status_payload(document.id)


from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    model: str | None = None
    session_id: str | None = None

@app.post("/api/documents/{doc_id}/ask", response_class=JSONResponse)
async def api_ask_question(doc_id: str, request: AskRequest):
    """Ask a question and return JSON response."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    session_id = request.session_id
    if not session_id:
        session = storage.create_chat_session(doc_id)
        session_id = session.id

    llm_client = AsyncOllamaClient(timeout=120, model=_normalize_model(request.model))
    try:
        chats = storage.list_chats(session_id, limit=5)
        chat_history = []
        for c in reversed(chats):
            chat_history.append({"role": "user", "content": c.question})
            chat_history.append({"role": "assistant", "content": c.answer})

        retrieval = await search_tree_async(question, tree, pages, llm_client)
        answer_result = await generate_answer_async(question, retrieval.retrieved_pages, llm_client, chat_history=chat_history)

        if is_no_info_answer(answer_result.answer):
            broad_retrieval = await search_tree_broad_async(question, tree, pages)
            if len(broad_retrieval.retrieved_pages) > len(retrieval.retrieved_pages):
                retry_answer = await generate_answer_async(question, broad_retrieval.retrieved_pages, llm_client, chat_history=chat_history)
                answer_result = retry_answer
                retrieval = broad_retrieval

        chat = storage.insert_chat(doc_id, session_id, question, answer_result.answer)

        all_trace_steps = retrieval.trace + [answer_result.trace_step]
        from private_pageindex.storage import RetrievalStepRecord
        for idx, step in enumerate(all_trace_steps):
            storage.insert_retrieval_step(RetrievalStepRecord(
                chat_id=chat.id,
                step_index=idx,
                action=step.action,
                node_id=step.node_id,
                pages=step.pages,
                reason=step.reason,
            ))
    finally:
        await llm_client.close()

    return {"status": "success", "chat_id": chat.id, "session_id": session_id}


@app.post("/api/documents/{doc_id}/ask/stream")
async def api_ask_question_stream(doc_id: str, request: AskRequest):
    """Stream retrieval trace events and answer tokens via SSE.

    Emits Server-Sent Events in the format ``data: {json}\\n\\n``:

    - ``{"type": "trace", "step": "inspect_tree", ...}``
    - ``{"type": "trace", "step": "select_nodes", "node_ids": [...], ...}``
    - ``{"type": "trace", "step": "fetch_pages", "node_id": "...", "pages": "...", ...}``
    - ``{"type": "token", "text": "..."}``
    - ``{"type": "done", "chat_id": "...", "answer": "...", "citations": [...]}``
    - ``{"type": "error", "detail": "..."}``
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        document = storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    session_id = request.session_id
    if not session_id:
        session = storage.create_chat_session(doc_id)
        session_id = session.id

    async def event_generator():
        llm_client = AsyncOllamaClient(timeout=600, model=_normalize_model(request.model))
        try:
            # --- Fetch Chat History ---
            chats = storage.list_chats(session_id, limit=5)
            chat_history = []
            for c in reversed(chats):
                chat_history.append({"role": "user", "content": c.question})
                chat_history.append({"role": "assistant", "content": c.answer})

            # --- Tree search with live trace emission ---
            retrieval = await search_tree_async(question, tree, pages, llm_client)

            # Emit each trace step as an SSE event
            for step in retrieval.trace:
                event_data: dict[str, Any] = {
                    "type": "trace",
                    "step": step.action,
                    "detail": step.reason,
                }
                if step.node_id:
                    event_data["node_id"] = step.node_id
                if step.node_ids:
                    event_data["node_ids"] = step.node_ids
                if step.pages:
                    event_data["pages"] = step.pages

                # For select_nodes, include the full list of selected node IDs
                if step.action == "select_nodes":
                    event_data["node_ids"] = retrieval.selected_node_ids

                yield f"data: {json.dumps(event_data)}\n\n"

            # --- Stream answer tokens ---
            full_answer_parts: list[str] = []
            page_range_str = "none"
            answer_page_count = 0

            async for event in generate_answer_stream(
                question, retrieval.retrieved_pages, llm_client, chat_history=chat_history
            ):
                if event["type"] == "context_ready":
                    answer_page_count = event["page_count"]
                    ctx_detail = f"Prepared {event['page_count']} page(s) ({event['total_chars']} chars) for answer generation."
                    ctx_event = {"type": "trace", "step": "context_ready", "detail": ctx_detail}
                    yield f"data: {json.dumps(ctx_event)}\n\n"
                elif event["type"] == "token":
                    full_answer_parts.append(event["text"])
                    tok_event = {"type": "token", "text": event["text"]}
                    yield f"data: {json.dumps(tok_event)}\n\n"
                elif event["type"] == "answer_done":
                    full_answer = event["answer"]
                    page_range_str = event["pages"]
                    answer_page_count = event["page_count"]

            if not full_answer_parts:
                full_answer = "I could not find relevant information in the document to answer this question."
            else:
                full_answer = "".join(full_answer_parts)

            # --- Persist chat and trace ---
            chat = storage.insert_chat(doc_id, session_id, question, full_answer)

            from private_pageindex.retrieval.tree_search import TraceStep as TreeTraceStep
            answer_trace_step = TreeTraceStep(
                action="generate_answer",
                node_id=None,
                pages=page_range_str,
                reason=f"Generated answer from {answer_page_count} page(s).",
            )
            all_trace_steps = retrieval.trace + [answer_trace_step]
            from private_pageindex.storage import RetrievalStepRecord
            for idx, step in enumerate(all_trace_steps):
                storage.insert_retrieval_step(RetrievalStepRecord(
                    chat_id=chat.id,
                    step_index=idx,
                    action=step.action,
                    node_id=step.node_id,
                    pages=step.pages,
                    reason=step.reason,
                ))

            # Extract citation page numbers from the answer
            import re
            citations = sorted(set(
                f"page {m}" for m in re.findall(r'\[?[pP]ages?\s+(\d+)', full_answer)
            ))

            done_event = {"type": "done", "chat_id": chat.id, "session_id": session_id, "answer": full_answer, "citations": citations}
            yield f"data: {json.dumps(done_event)}\n\n"

        except Exception as exc:
            err_event = {"type": "error", "detail": str(exc)}
            yield f"data: {json.dumps(err_event)}\n\n"
        finally:
            await llm_client.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/documents/{doc_id}/delete", response_class=JSONResponse)
def api_delete_document_post(doc_id: str):
    """Delete a document and all associated data via POST."""
    return _delete_document_internal(doc_id)


@app.delete("/api/documents/{doc_id}/delete", response_class=JSONResponse)
def api_delete_document_delete(doc_id: str):
    """Delete a document and all associated data via DELETE endpoint."""
    return _delete_document_internal(doc_id)


@app.delete("/api/documents/{doc_id}", response_class=JSONResponse)
def api_delete_document_rest(doc_id: str):
    """Delete a document and all associated data via REST DELETE."""
    return _delete_document_internal(doc_id)


def _delete_document_internal(doc_id: str) -> dict[str, str]:
    try:
        storage.get_document(doc_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage.delete_document(doc_id)
    return {"status": "success", "message": f"Document {doc_id} has been deleted."}


# ---------------------------------------------------------------------------
# SPA Static Serving — Auto-detect Vite production build
# ---------------------------------------------------------------------------
# When frontend/dist/ exists (after running `npm run build` in the frontend
# directory), serve the built assets and add a catch-all that returns
# index.html for any non-API path (SPA client-side routing).
# When dist/ does not exist (dev mode with Vite proxy), this block is
# silently skipped and the dev proxy continues to work normally.

_project_root = Path(__file__).resolve().parent.parent.parent
_frontend_dist = _project_root / "frontend" / "dist"

if _frontend_dist.is_dir() and (_frontend_dist / "index.html").is_file():
    from fastapi.responses import FileResponse

    # Serve built assets (JS, CSS, fonts, images) under /assets/*
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="spa-assets")

    # Serve files in dist root (favicon, fonts, etc.)
    app.mount("/fonts", StaticFiles(directory=_frontend_dist / "fonts"), name="spa-fonts") if (_frontend_dist / "fonts").is_dir() else None

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_catch_all(full_path: str):
        """SPA catch-all: serve index.html for any non-API route.

        This runs AFTER all explicit API routes, so /api/* endpoints
        are never intercepted. Only unmatched paths (e.g. /documents/abc)
        hit this handler.
        """
        # Try to serve the exact file first (e.g. /favicon.svg, /logo.svg)
        dist_root = _frontend_dist.resolve()
        rel_path = Path(full_path)

        # Reject absolute paths and traversal attempts; only allow safe relative paths.
        if rel_path.is_absolute() or any(part == ".." for part in rel_path.parts):
            candidate = None
        else:
            candidate = (dist_root / rel_path).resolve()
            try:
                candidate.relative_to(dist_root)
            except ValueError:
                candidate = None

        if candidate is not None and candidate.is_file() and not full_path.startswith("api"):
            return FileResponse(candidate)
        # Otherwise return index.html for client-side routing
        return FileResponse(_frontend_dist / "index.html")

