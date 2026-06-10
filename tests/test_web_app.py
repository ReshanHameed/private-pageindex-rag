"""Tests for the local web app."""

import uuid
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from private_pageindex.ingest.pipeline import index_pdf
from private_pageindex.retrieval.answering import AnswerResult
from private_pageindex.retrieval.tree_search import RetrievalResult, TraceStep
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


def make_test_app():
    """Create a test-scoped FastAPI app with its own storage directory."""
    import importlib
    import private_pageindex.web.app as web_module

    test_dir = fresh_runtime_dir()
    test_storage = LocalStorage(test_dir)
    test_storage.initialize()

    # Patch the module-level storage with our test storage.
    original_storage = web_module.storage
    web_module.storage = test_storage
    client = TestClient(web_module.app)
    return client, test_storage, test_dir, web_module, original_storage


def teardown_test_app(web_module, original_storage):
    """Restore original storage on the web module."""
    web_module.storage = original_storage


def test_index_page_renders_empty_document_list():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/")
        assert response.status_code == 200
        assert "Private" in response.text or "Documents" in response.text
        assert "No documents" in response.text or "Upload" in response.text
    finally:
        teardown_test_app(web_module, orig)


def test_index_page_renders_documents_after_indexing():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        source_dir = fresh_runtime_dir()
        pdf_path = create_pdf(
            source_dir / "manual.pdf",
            ["1 Introduction\nOverview."],
        )
        index_pdf(pdf_path, storage, max_pages_per_node=10)

        response = client.get("/")
        assert response.status_code == 200
        assert "manual.pdf" in response.text
    finally:
        teardown_test_app(web_module, orig)


def test_index_page_renders_model_picker_and_processing_progress():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        document = storage.create_document(filename="manual.pdf", status="processing")
        storage.update_document_progress(
            document.id,
            progress_percent=20,
            progress_stage="extracting text",
        )

        response = client.get("/")

        assert response.status_code == 200
        assert 'id="ollama-model-select"' in response.text
        assert 'name="model"' in response.text
        assert 'class="progress-bar"' in response.text
        assert 'data-doc-id="' + document.id + '"' in response.text
        assert "extracting text" in response.text
    finally:
        teardown_test_app(web_module, orig)


def test_document_detail_page_shows_tree_and_chat():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        source_dir = fresh_runtime_dir()
        pdf_path = create_pdf(
            source_dir / "manual.pdf",
            [
                "1 Introduction\nThis is the introduction.",
                "2 Safety\nWear protective equipment.",
            ],
        )
        result = index_pdf(pdf_path, storage, max_pages_per_node=10)

        response = client.get(f"/documents/{result.doc_id}")
        assert response.status_code == 200
        assert "manual.pdf" in response.text
        assert "Introduction" in response.text
        assert "Ask" in response.text or "question" in response.text.lower()
    finally:
        teardown_test_app(web_module, orig)


def test_document_detail_returns_404_for_unknown_doc():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/documents/nonexistent-id")
        assert response.status_code == 404
    finally:
        teardown_test_app(web_module, orig)


def test_ollama_status_endpoint_returns_json():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/api/ollama-status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    finally:
        teardown_test_app(web_module, orig)


def test_status_endpoint_returns_progress_and_elapsed_time():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        document = storage.create_document(filename="manual.pdf", status="processing")
        storage.update_document_progress(
            document.id,
            progress_percent=45,
            progress_stage="building tree",
        )

        response = client.get(f"/api/documents/{document.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document.id
        assert data["status"] == "processing"
        assert data["progress_percent"] == 45
        assert data["progress_stage"] == "building tree"
        assert data["elapsed_seconds"] >= 0
    finally:
        teardown_test_app(web_module, orig)


def test_ollama_models_endpoint_returns_available_model_names(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()

    class FakeAsyncOllamaClient:
        def __init__(self, *args, **kwargs):
            pass

        async def check_health(self):
            return {
                "status": "connected",
                "model": "gemma4:e4b",
                "model_available": True,
                "models": ["gemma4:e4b", "llama3.2:latest"],
            }

        async def close(self):
            pass

    monkeypatch.setattr(web_module, "AsyncOllamaClient", FakeAsyncOllamaClient)
    try:
        response = client.get("/api/ollama-models")

        assert response.status_code == 200
        assert response.json() == {
            "status": "connected",
            "default_model": "gemma4:e4b",
            "models": ["gemma4:e4b", "llama3.2:latest"],
        }
    finally:
        teardown_test_app(web_module, orig)


def test_upload_creates_processing_document_and_passes_selected_model(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()
    captured: dict[str, object] = {}

    class FakeOllamaClient:
        def __init__(self, *args, **kwargs):
            self.model = kwargs.get("model")
            captured["model"] = self.model

        def close(self):
            pass

    def fake_index_pdf(path, storage_arg, **kwargs):
        captured["path"] = path
        captured["existing_doc_id"] = kwargs["existing_doc_id"]
        captured["llm_model"] = kwargs["llm_client"].model
        storage_arg.update_document_status(
            kwargs["existing_doc_id"],
            "completed",
            page_count=1,
        )
        return None

    monkeypatch.setattr(web_module, "OllamaClient", FakeOllamaClient)
    monkeypatch.setattr(web_module, "index_pdf", fake_index_pdf)
    try:
        response = client.post(
            "/upload",
            data={"model": "llama3.2:latest"},
            files={"file": ("manual.pdf", b"%PDF-1.4 fake", "application/pdf")},
            follow_redirects=False,
        )

        assert response.status_code == 303
        documents = storage.list_documents()
        assert len(documents) == 1
        assert captured["existing_doc_id"] == documents[0].id
        assert captured["llm_model"] == "llama3.2:latest"
    finally:
        teardown_test_app(web_module, orig)


def test_ask_question_passes_selected_model(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()
    document = storage.create_document(filename="manual.pdf", status="completed", page_count=1)
    storage.write_pages(document.id, [{"page_number": 1, "text": "Safety text.", "char_count": 12}])
    storage.write_tree(
        document.id,
        {
            "doc_id": document.id,
            "nodes": [
                {
                    "node_id": "0001",
                    "title": "Safety",
                    "start_page": 1,
                    "end_page": 1,
                    "summary": "Safety.",
                    "nodes": [],
                }
            ],
        },
    )
    captured: dict[str, object] = {}

    class FakeAsyncOllamaClient:
        def __init__(self, *args, **kwargs):
            self.model = kwargs.get("model")
            captured["model"] = self.model

        async def close(self):
            pass

    async def fake_search_tree_async(question, tree, pages, llm_client):
        captured["search_model"] = llm_client.model
        return RetrievalResult(
            selected_node_ids=["0001"],
            retrieved_pages=pages,
            trace=[
                TraceStep(
                    action="inspect_tree",
                    node_id=None,
                    pages=None,
                    reason="Inspected.",
                )
            ],
        )

    async def fake_generate_answer_async(question, retrieved_pages, llm_client):
        captured["answer_model"] = llm_client.model
        return AnswerResult(
            answer="Use protective equipment. [page 1]",
            trace_step=TraceStep(
                action="generate_answer",
                node_id=None,
                pages="1-1",
                reason="Answered.",
            ),
        )

    monkeypatch.setattr(web_module, "AsyncOllamaClient", FakeAsyncOllamaClient)
    monkeypatch.setattr(web_module, "search_tree_async", fake_search_tree_async)
    monkeypatch.setattr(web_module, "generate_answer_async", fake_generate_answer_async)
    try:
        response = client.post(
            f"/documents/{document.id}/ask",
            data={"question": "What about safety?", "model": "llama3.2:latest"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert captured["model"] == "llama3.2:latest"
        assert captured["search_model"] == "llama3.2:latest"
        assert captured["answer_model"] == "llama3.2:latest"
    finally:
        teardown_test_app(web_module, orig)


def test_ask_question_retries_broad_on_no_info(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()
    document = storage.create_document(filename="manual.pdf", status="completed", page_count=2)
    storage.write_pages(document.id, [
        {"page_number": 1, "text": "Cover page.", "char_count": 11},
        {"page_number": 2, "text": "Real safety text.", "char_count": 17}
    ])
    storage.write_tree(
        document.id,
        {
            "doc_id": document.id,
            "nodes": [
                {
                    "node_id": "0001",
                    "title": "Cover",
                    "start_page": 1,
                    "end_page": 1,
                    "summary": "Cover.",
                    "nodes": [],
                },
                {
                    "node_id": "0002",
                    "title": "Safety",
                    "start_page": 2,
                    "end_page": 2,
                    "summary": "Safety.",
                    "nodes": [],
                }
            ],
        },
    )

    calls = []

    class FakeAsyncOllamaClient:
        def __init__(self, *args, **kwargs):
            pass

        async def close(self):
            pass

    async def fake_search_tree_async(question, tree, pages, llm_client):
        calls.append("search_tree_async")
        # Return page 1 (which lacks safety info)
        return RetrievalResult(
            selected_node_ids=["0001"],
            retrieved_pages=[pages[0]],
            trace=[TraceStep("inspect_tree", None, None, "Inspected.")],
        )

    async def fake_generate_answer_async(question, retrieved_pages, llm_client):
        calls.append("generate_answer_async")
        # If it includes page 2, return real answer
        if any(p["page_number"] == 2 for p in retrieved_pages):
            return AnswerResult(
                answer="Wear safety equipment [page 2].",
                trace_step=TraceStep("generate_answer", None, "2-2", "Answered."),
            )
        return AnswerResult(
            answer="I could not find any information about safety in the text.",
            trace_step=TraceStep("generate_answer", None, "1-1", "No information found."),
        )

    async def fake_search_tree_broad_async(question, tree, pages, llm_client=None):
        calls.append("search_tree_broad_async")
        return RetrievalResult(
            selected_node_ids=["0001", "0002"],
            retrieved_pages=pages,
            trace=[TraceStep("search_tree_broad", None, None, "Broadened.")],
        )

    monkeypatch.setattr(web_module, "AsyncOllamaClient", FakeAsyncOllamaClient)
    monkeypatch.setattr(web_module, "search_tree_async", fake_search_tree_async)
    monkeypatch.setattr(web_module, "generate_answer_async", fake_generate_answer_async)
    monkeypatch.setattr(web_module, "search_tree_broad_async", fake_search_tree_broad_async)

    try:
        response = client.post(
            f"/documents/{document.id}/ask",
            data={"question": "What about safety?"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert calls == [
            "search_tree_async",
            "generate_answer_async",
            "search_tree_broad_async",
            "generate_answer_async"
        ]

        sessions = storage.list_chat_sessions(document.id)
        chats = storage.list_chats(sessions[0].id)
        assert len(chats) == 1
        assert "page 2" in chats[0].answer
    finally:
        teardown_test_app(web_module, orig)


def test_api_list_documents():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        # Create a document
        doc1 = storage.create_document(filename="first.pdf", status="completed", page_count=10)
        doc2 = storage.create_document(filename="second.pdf", status="processing")
        
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # list_documents sorts newest first, so doc2 is first
        assert data[0]["id"] == doc2.id
        assert data[0]["filename"] == "second.pdf"
        assert data[0]["status"] == "processing"
        assert data[1]["id"] == doc1.id
        assert data[1]["filename"] == "first.pdf"
        assert data[1]["status"] == "completed"
        assert data[1]["page_count"] == 10
    finally:
        teardown_test_app(web_module, orig)


def test_api_upload_pdf(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()
    
    class FakeOllamaClient:
        def __init__(self, *args, **kwargs):
            pass
        def close(self):
            pass
            
    def fake_index_pdf(path, storage_arg, **kwargs):
        storage_arg.update_document_status(
            kwargs["existing_doc_id"],
            "completed",
            page_count=2,
        )
        return None

    monkeypatch.setattr(web_module, "OllamaClient", FakeOllamaClient)
    monkeypatch.setattr(web_module, "index_pdf", fake_index_pdf)
    try:
        response = client.post(
            "/api/upload",
            data={"model": "gemma4:e4b"},
            files={"file": ("manual.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "manual.pdf"
        assert data["status"] == "processing"
        assert data["progress_percent"] == 5
        assert data["progress_stage"] == "saving upload"
    finally:
        teardown_test_app(web_module, orig)


def test_api_upload_pdf_invalid_extension():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.post(
            "/api/upload",
            files={"file": ("manual.txt", b"plain text", "text/plain")},
        )
        assert response.status_code == 400
        assert "Only .pdf files" in response.json()["detail"]
    finally:
        teardown_test_app(web_module, orig)


def test_api_delete_document():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        # Create documents to delete via different endpoints
        doc1 = storage.create_document(filename="doc1.pdf", status="completed")
        doc2 = storage.create_document(filename="doc2.pdf", status="completed")
        doc3 = storage.create_document(filename="doc3.pdf", status="completed")
        
        # Test DELETE /api/documents/{id}/delete
        resp1 = client.delete(f"/api/documents/{doc1.id}/delete")
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "success"
        
        # Test POST /api/documents/{id}/delete
        resp2 = client.post(f"/api/documents/{doc2.id}/delete")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "success"
        
        # Test DELETE /api/documents/{id}
        resp3 = client.delete(f"/api/documents/{doc3.id}")
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "success"
        
        # Verify all are deleted from storage
        assert len(storage.list_documents()) == 0
        
        # Test 404
        resp4 = client.delete("/api/documents/nonexistent/delete")
        assert resp4.status_code == 404
    finally:
        teardown_test_app(web_module, orig)


def test_api_get_document_chats_with_traces():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        # Create a document, a chat, and a retrieval step
        doc = storage.create_document(filename="test.pdf", status="completed")
        session = storage.create_chat_session(doc.id)
        chat = storage.insert_chat(doc.id, session.id, "Is this a test?", "Yes, it is.")
        
        from private_pageindex.storage import RetrievalStepRecord
        storage.insert_retrieval_step(RetrievalStepRecord(
            chat_id=chat.id,
            step_index=0,
            action="inspect_tree",
            node_id="0001",
            pages="1-2",
            reason="Reasoning text.",
        ))

        # Request chats via API
        response = client.get(f"/api/documents/{doc.id}/sessions/{session.id}/chats")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["id"] == chat.id
        assert data[0]["question"] == "Is this a test?"
        assert data[0]["answer"] == "Yes, it is."
        assert data[0]["created_at"] == chat.created_at
        
        trace_steps = data[0]["trace_steps"]
        assert len(trace_steps) == 1
        assert trace_steps[0]["step_index"] == 0
        assert trace_steps[0]["action"] == "inspect_tree"
        assert trace_steps[0]["node_id"] == "0001"
        assert trace_steps[0]["pages"] == "1-2"
        assert trace_steps[0]["reason"] == "Reasoning text."
        assert trace_steps[0]["created_at"] == chat.created_at
    finally:
        teardown_test_app(web_module, orig)


def test_api_ask_document_stream(monkeypatch):
    client, storage, test_dir, web_module, orig = make_test_app()
    document = storage.create_document(filename="manual.pdf", status="completed", page_count=1)
    storage.write_pages(document.id, [{"page_number": 1, "text": "Safety text.", "char_count": 12}])
    storage.write_tree(
        document.id,
        {
            "doc_id": document.id,
            "nodes": [
                {
                    "node_id": "0001",
                    "title": "Safety",
                    "start_page": 1,
                    "end_page": 1,
                    "summary": "Safety.",
                    "nodes": [],
                }
            ],
        },
    )

    class FakeAsyncOllamaClient:
        def __init__(self, *args, **kwargs):
            pass

        async def close(self):
            pass

    async def fake_search_tree_async(question, tree, pages, llm_client):
        return RetrievalResult(
            selected_node_ids=["0001"],
            retrieved_pages=pages,
            trace=[
                TraceStep(
                    action="inspect_tree",
                    node_id=None,
                    pages=None,
                    reason="Inspected.",
                )
            ],
        )

    async def fake_generate_answer_stream(question, retrieved_pages, llm_client, **kwargs):
        yield {"type": "context_ready", "page_count": 1, "total_chars": 12}
        yield {"type": "token", "text": "This "}
        yield {"type": "token", "text": "is "}
        yield {"type": "token", "text": "test. "}
        yield {"type": "answer_done", "answer": "This is test. [page 1]", "pages": "1-1", "page_count": 1}

    monkeypatch.setattr(web_module, "AsyncOllamaClient", FakeAsyncOllamaClient)
    monkeypatch.setattr(web_module, "search_tree_async", fake_search_tree_async)
    monkeypatch.setattr(web_module, "generate_answer_stream", fake_generate_answer_stream)

    try:
        with client.stream(
            "POST",
            f"/api/documents/{document.id}/ask/stream",
            json={"question": "What is this?", "model": "llama3.2:latest"},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            lines = [line for line in response.iter_lines() if line]
            print(lines)
            if not any("context_ready" in line for line in lines):
                print("LINES:", lines)
            assert any("context_ready" in line for line in lines)
            assert any("This" in line for line in lines)
            assert any("done" in line for line in lines)
            
            # Check chat was persisted
            sessions = storage.list_chat_sessions(document.id)
            chats = storage.list_chats(sessions[0].id)
            assert len(chats) == 1
            assert chats[0].question == "What is this?"
            assert chats[0].answer == "This is test. "
    finally:
        teardown_test_app(web_module, orig)



