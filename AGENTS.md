# Agent Operating Notes

This repository is intended to be worked on by AI coding agents. Read this file first, then read `docs/AGENT_MEMORY.md` before making changes.

## Project Identity

- Project name: `private-pageindex-rag`.
- Current workspace folder: `D:\Projects\private-pageindex-rag`.
- Purpose: private, local-first PageIndex-style RAG for selectable-text PDFs.
- Runtime boundary: local filesystem, SQLite, FastAPI, PyMuPDF, and local Ollama only.
- Do not introduce PageIndex Cloud, OpenAI, Anthropic, hosted MCP servers, hosted inference APIs, vector databases, OCR, or cloud deployment unless the user explicitly asks for that direction.

## Required Startup Flow

1. Read `README.md` for setup and usage.
2. Read `docs/AGENT_MEMORY.md` for the current feature set, latest work, invariants, and open tasks.
3. Read the most relevant deeper doc before changing code:
   - `docs/PROJECT.md` for product scope.
   - `docs/ARCHITECTURE.md` for module boundaries.
   - `docs/TROUBLESHOOTING.md` for expected verification commands and known runtime issues.
   - `docs/STRUCTURE.md` for repository layout.
4. Inspect the files you will modify. Do not rely only on the memory file.

## Development Rules

- Keep changes narrow and aligned with the existing module boundaries.
- Preserve the local privacy guarantee: document text must stay local and inference must use the configured local Ollama endpoint.
- Preserve existing public command and route contracts unless the user asks for a breaking change.
- Runtime/generated folders must not be committed: `.venv/`, `.tmp/`, `data/`, `test_runtime/`, `__pycache__/`, `.pytest_cache/`, and `*.egg-info/`.
- Prefer focused tests for the touched behavior, then run the broader relevant suite.
- If changing tree-building behavior, protect backward-compatible tree JSON fields: `node_id`, `title`, `start_page`, `end_page`, `summary`, and `nodes`.
- If adding new tree metadata, keep it additive.

## Common Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pytest tests/test_tree_builder.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py tests/test_cli.py -v
.\.venv\Scripts\python.exe -m uvicorn private_pageindex.web.app:app --reload --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m private_pageindex.cli serve
```

## Memory Update Rule

At the end of each agent session that changes code, tests, docs, configuration, or project direction, update `docs/AGENT_MEMORY.md`.

The update must include:

- Date.
- Short task title.
- What changed.
- Files changed.
- Verification run and result.
- Any new invariants, decisions, risks, or follow-up tasks.

Keep the memory factual and compact. Do not paste long logs, stack traces, or full command output unless the exact text is important for future debugging.

