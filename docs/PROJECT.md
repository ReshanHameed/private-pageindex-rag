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

## V1 Boundaries

- Text PDFs only.
- No OCR for scanned PDFs.
- No cloud deployment.
- No multi-document ranking.
- No vector database.
- No table-specific extraction.
- No external inference APIs.

