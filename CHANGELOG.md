# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-06-11

This is the initial release of **Private PageIndex RAG**, a fully private, local-first document retrieval and interactive answering system.

### Added
- **Hierarchical Document Indexing**: Replaces vector chunking with structural PDF tree building (`tree.json`) using PyMuPDF (Fitz) for selectable-text extraction.
- **Tree-Guided Search & Retrieval**: Uses local LLM (Ollama) to traverse the document tree structures and retrieve full, contiguous pages instead of fragmented blocks.
- **Grounded Chat with Citations**: Streams answers in real-time with case-insensitive `[page N]` clickable citations.
- **Interactive Spatial Knowledge Graph**: Monospaced "Terminal Scholar" UI featuring dynamic force-directed and circular D3 visualizations of the document tree.
- **Live Retrieval Debugger & Tracer**: Animates RAG retrieval steps (inspect tree, select nodes, fetch pages) directly on the knowledge graph in real-time.
- **Conversational Memory**: Supports multi-turn chat context (sends last 5 messages to the LLM) and multiple chat session threads per document.
- **FastAPI / Uvicorn Backend**: High-performance backend serving as both REST API and single-origin static file host for React production builds.
- **Granular Progress Reporting**: Real-time progress updates with specific ingestion sub-stages (e.g. `detecting headings`, `normalizing structures`, `generating summaries`, `enhancing node N of M`) and animated progress bars.
- **SQLite Performance Optimization**: SQLite database indexes added on all primary foreign keys (`idx_retrieval_steps_chat_id`, `idx_chats_session_id`, etc.) delivering a 16.5x query speedup.
- **FastAPI Event-Loop Offloading**: Converted heavy synchronous CPU/IO endpoints to standard synchronous functions to offload them to FastAPI's thread pool, resolving UI navigation lag.
- **Robust Parsing for Messy PDFs**: Disambiguates duplicate headings, suppresses corporate headers/footers, handles empty/blank pages, and tolerates multiline headings.
- **Automated Test Suite**: 116 unit and integration tests covering extraction, storage, LLM clients, tree search, and API routing.
- **Developer Continuity Support**: Structured `AGENTS.md` and `docs/AGENT_MEMORY.md` to support seamless handoff for AI agents and open-source contributors.
