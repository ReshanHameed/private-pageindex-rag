# Project Overview

Recommended project name: `private-pageindex-rag`

This repository is a private, local-first PageIndex-style RAG prototype for text-based PDFs. It indexes selectable-text PDFs on the local machine, builds a local document tree, stores document artifacts in SQLite and the filesystem, and uses a local Ollama server for retrieval decisions and answer generation.

For a detailed analysis of how this project compares to Traditional RAG, the exact problems it solves, and performance/cost metrics, see [PROBLEM_SOLVED.md](PROBLEM_SOLVED.md).

The project is not a PageIndex Cloud integration and does not call hosted model providers for inference. The intended LLM runtime is the local Ollama API at `http://localhost:11434`.

## Current Capabilities

- Upload and index local text PDFs through a FastAPI web app.
- Index uploaded PDFs in the background with visible progress, stage, and elapsed time.
- Ingest PDFs from the CLI.
- Extract selectable PDF text with PyMuPDF.
- Build a PageIndex-style tree from headings or fallback page ranges.
- Store PDFs, extracted page text, trees, document metadata, chats, and retrieval traces locally.
- Organize conversations into multiple persistent chat sessions (threads) per document with conversational memory.
- Explore document structures using an interactive spatial knowledge graph (force-directed and circular layouts).
- View live citation tracing that animates retrieval steps directly on the knowledge graph nodes in real time.
- Read structured answers parsed by a custom markdown renderer, featuring interactive, clickable `[page N]` citation tags.
- Delete indexed documents, chat sessions, and their associated local database/file assets.
- Check local Ollama reachability through a lightweight status endpoint.
- Select any available local Ollama model from the web UI for indexing and chat.
- Expose the pipeline to external agents through a local MCP (Model Context Protocol) server that reuses the same local functions and local Ollama endpoint.
- Stage PDFs for filename-based ingestion through a local inbox folder (`inbox_dir` / `INBOX_DIR`, default `data/inbox/`).
- Discover MCP connection details from an in-app, read-only **Connect** screen (`/connect`) that lists the live tool catalog and copy-paste client configs.

## MCP Agent Access

- MCP server module: `private_pageindex/mcp_server.py` (FastMCP), started with the CLI `serve-mcp` command (stdio by default, `--http` for a shared streamable-HTTP instance).
- Tools exposed to agents: `list_documents`, `get_document`, `get_document_tree`, `list_inbox`, `ingest_pdf`, `get_ingest_status`, `retrieve_context`, `ask`, `delete_document`, `ollama_status`.
- The MCP server is packaged as an optional extra (`pip install -e .[mcp]`) and a console script (`private-pageindex-mcp`).
- Web endpoints backing the Connect screen (read-only): `GET /api/mcp/info` and `GET /api/mcp/http-status`.
- Optional bearer authentication for the HTTP transport via `MCP_AUTH_TOKEN`.

## V1 Boundaries

- Text PDFs only.
- No OCR for scanned PDFs.
- No cloud deployment.
- No multi-document ranking.
- No vector database.
- No table-specific extraction.
- No external inference APIs.
- Local MCP only: the built-in MCP server is in scope, but hosted/cloud MCP servers and hosted inference APIs are not.

