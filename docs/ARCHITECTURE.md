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
| `private_pageindex/web/app.py` | FastAPI routes for upload, delete, document metadata, chats, live SSE streaming, Ollama status, and the read-only MCP Connect endpoints (`GET /api/mcp/info`, `GET /api/mcp/http-status`). Serves the built SPA static assets in production. |
| `private_pageindex/documents.py` | Shared document-level operations (deletion cascade) used by both the web app and the MCP server. |
| `private_pageindex/mcp_server.py` | MCP server (FastMCP) exposing ingest, list, tree, retrieve-context, ask, delete, status, and inbox tools over stdio and streamable HTTP for external agents. |
| `private_pageindex/cli.py` | CLI commands for ingesting, asking, serving the web app, and serving the MCP server (`serve-mcp`). |
| `frontend/` | React 19 + Vite 6 + TypeScript + Tailwind CSS 4 frontend SPA. Integrates d3-force for knowledge graph visualization, Zustand for state management, and anime.js for UI transitions. |
| `frontend/src/pages/ConnectPage.tsx` + `frontend/src/components/connect/` | In-app MCP **Connect** screen: `ConfigBlock`, `AgentCard`, `McpStatusBar`, and `ToolCatalog` render per-agent config and the live tool catalog from `/api/mcp/info`. |

## Storage Layout

Default `DATA_DIR` is `data`.

```text
data/
  private_pageindex.db
  inbox/
    <dropped>.pdf        # optional: PDFs staged for MCP ingest by filename
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

## MCP Server Layer

`private_pageindex/mcp_server.py` exposes the existing local operations as MCP tools so external agents (Claude Desktop, Codex, Antigravity IDE, others) can drive the pipeline. It is a thin wrapper: each tool calls the same reusable functions (`index_pdf`, `search_tree`, `generate_answer`, `LocalStorage`, `delete_document_and_assets`) the CLI and web app use, so the privacy boundary is unchanged — text stays local and inference goes only to the configured local Ollama endpoint.

- Tools (10): `list_documents`, `get_document`, `get_document_tree`, `list_inbox`, `ingest_pdf`, `get_ingest_status`, `retrieve_context`, `ask`, `delete_document`, `ollama_status`.
- Config fields (in `config.py`): `inbox_dir` (`INBOX_DIR`), `mcp_http_host` (`MCP_HTTP_HOST`), `mcp_http_port` (`MCP_HTTP_PORT`), `mcp_auth_token` (`MCP_AUTH_TOKEN`).
- Packaging: optional extra `pip install -e .[mcp]` (also in `[dev]`) plus a `private-pageindex-mcp` console script. `cli.py` imports `mcp_server` lazily so the core install works without the `mcp` package.
- Transports: stdio (default, one server per agent) and streamable HTTP (`--http`, one shared instance) bound to `127.0.0.1` by default, with an optional `MCP_AUTH_TOKEN` bearer gate. HTTP endpoint path is `/mcp`.
- Ingest is non-blocking: `ingest_pdf` creates the `processing` document row, returns a `doc_id` immediately, and runs `index_pdf` in a background daemon thread. Agents poll `get_ingest_status`. PDFs can be supplied by local path or by filename from the inbox folder (`INBOX_DIR`, default `data/inbox/`).
- `retrieve_context` returns raw relevant page text plus page citations (no LLM answer); `ask` returns a grounded answer with `[page N]` citations. Both persist a chat + retrieval trace so agent-initiated queries appear in the web UI and trace debugger.
- Web UI: a read-only **Connect** screen (`/connect`) lists per-agent connection config and the live tool catalog. It is backed by two read-only endpoints in `web/app.py`: `GET /api/mcp/info` (transports + tool catalog via `mcp.list_tools()`, guarded so it degrades to `installed: false` when the optional `mcp` package is absent) and `GET /api/mcp/http-status` (an httpx reachability probe of the shared HTTP endpoint). Neither endpoint controls the MCP process or exposes the auth token value.
