# Architecture

## System Flow

```text
Text PDF
  -> PyMuPDF selectable-text extraction
  -> PageIndex-style tree builder
  -> SQLite and filesystem persistence
  -> Ollama tree-search node selection & SSE token streaming
  -> React SPA frontend (visualized knowledge graph, live citations, streaming chat UI)
```

## Main Modules

| Path | Responsibility |
| --- | --- |
| `private_pageindex/config.py` | Runtime settings loaded from environment variables or `.env`. |
| `private_pageindex/storage.py` | SQLite schema (documents, nodes, chat_sessions, chats, retrieval_steps), connection context manager, and filesystem artifact paths. |
| `private_pageindex/ingest/pdf_text.py` | Local extraction for selectable-text PDFs using PyMuPDF. |
| `private_pageindex/ingest/pipeline.py` | End-to-end indexing pipeline: create document row, copy upload, extract text, build tree with progress updates, save page/tree files, insert node rows. |
| `private_pageindex/indexing/tree_builder.py` | Deterministic heading detection, fallback page-range trees, node summaries, and optional Ollama enhancement. |
| `private_pageindex/llm/ollama.py` | Synchronous and asynchronous local Ollama client for text, JSON, and health checks. |
| `private_pageindex/retrieval/tree_search.py` | Tree-guided retrieval using local Ollama JSON selection and trace recording. |
| `private_pageindex/retrieval/answering.py` | Grounded answer generation from retrieved page text with conversational memory. |
| `private_pageindex/web/app.py` | FastAPI routes for upload, delete, document metadata, chats, live SSE streaming, and Ollama status. Serves the built SPA static assets in production. |
| `private_pageindex/cli.py` | CLI commands for ingesting, asking, and serving the app. |
| `frontend/` | React 19 + Vite 6 + TypeScript + Tailwind CSS 4 frontend SPA. Integrates d3-force for knowledge graph visualization, Zustand for state management, and anime.js for UI transitions. |

## Storage Layout

Default `DATA_DIR` is `data`.

```text
data/
  private_pageindex.db
  uploads/
    <doc_id>.pdf
  documents/
    <doc_id>/
      pages.jsonl
      tree.json
```

SQLite tables:

| Table | Purpose |
| --- | --- |
| `documents` | Document filename, status, page count, creation time, error text, indexing progress, stage, and timing fields. |
| `nodes` | Flattened tree node metadata. |
| `chat_sessions` | Conversational threads/sessions grouped per document. |
| `chats` | Stored question and answer pairs belonging to a chat session. |
| `retrieval_steps` | Trace records for tree inspection, node selection, page fetching, and answer generation. |

## Error Handling

- PDF extraction failures are raised as `PdfExtractionError`.
- Indexing failures are wrapped as `PipelineError` and recorded on the document row with status `failed`.
- Ollama connection, timeout, model-not-found, and invalid-response cases are wrapped in explicit `OllamaError` subclasses.
- The web app marks documents stuck in `processing` as `failed` during startup recovery.

## Runtime Privacy Boundary

The application stores document contents under the local `DATA_DIR` and uses the configured local Ollama endpoint for inference. It does not send document text to hosted inference providers.

Web uploads create a `processing` document row, save the uploaded PDF locally, and schedule indexing as a background task. Progress fields on the `documents` row expose the current stage, percentage, and elapsed time through `/api/documents/{doc_id}/status`.

The frontend is completely offline-first: it self-hosts all fonts (Space Grotesk, Geist Sans, JetBrains Mono) as `.woff2` files inside `frontend/public/fonts/` and makes zero external HTTP requests to CDN servers.
