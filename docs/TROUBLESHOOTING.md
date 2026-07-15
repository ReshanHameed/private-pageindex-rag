# Troubleshooting

## Start Everything (Recommended)

One command starts Ollama (if needed), backend, frontend, and shared MCP HTTP:

```powershell
.\.venv\Scripts\python.exe -m private_pageindex.cli dev
```

Or:

```powershell
.\scripts\dev.ps1
```

Open **http://localhost:5173**. Press **Ctrl+C** to stop managed services.

Flags:
- `--no-ollama` — skip starting Ollama (use when the tray app is already running)
- `--no-frontend` — backend + MCP HTTP only
- `--no-mcp` — Ollama + backend + frontend only

If ports 8000 or 5173 are in use, stop any manually started backend/frontend first.

## Run The Full Test Suite

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected current result: 132 passing tests. Re-run before relying on this count; it drifts as tests are added.

## Start The Backend Web App

```powershell
.\.venv\Scripts\python.exe -m uvicorn private_pageindex.web.app:app --reload --host 127.0.0.1 --port 8000
```

The backend API runs at:

```text
http://127.0.0.1:8000
```

## Start The Frontend Client

Navigate to the `frontend/` directory and start the Vite development server:

```powershell
cd frontend
npm run dev
```

The frontend client runs at:

```text
http://localhost:5173
```

API requests (e.g. `/api/*`) are proxied automatically to the backend on port 8000.

## Build Frontend for Production

Compile production-optimized client assets:

```powershell
cd frontend
npm run build
```

This compiles client files to `frontend/dist/`. The FastAPI backend will automatically serve these static files when you start the backend web app, providing a single-origin server deployment.

## Start Through The CLI

```powershell
.\.venv\Scripts\python.exe -m private_pageindex.cli serve
```

## MCP Server (Connect External Agents)

The MCP server exposes the pipeline to external agents. It requires the optional
`mcp` package.

Install the extra:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[mcp]
```

Start it over stdio (each agent launches its own instance):

```powershell
.\.venv\Scripts\python.exe -m private_pageindex.cli serve-mcp
```

Start a single shared HTTP instance (default bind `127.0.0.1:8765`, endpoint `/mcp`):

```powershell
.\.venv\Scripts\python.exe -m private_pageindex.cli serve-mcp --http --host 127.0.0.1 --port 8765
```

### Connect Screen Shows "Not Installed" / Empty Tool List

The web UI **Connect** screen (sidebar → Connect) reads:

```text
http://127.0.0.1:8000/api/mcp/info
```

If it reports `installed: false` or an empty tool list, the optional `mcp`
package is missing. Install it with `pip install -e .[mcp]` and restart the web
app. This endpoint is read-only and never returns the `MCP_AUTH_TOKEN` value
(only an `auth_required` boolean).

### Connect Screen Shows HTTP "Not Running"

The Connect screen probes the shared HTTP endpoint via:

```text
http://127.0.0.1:8000/api/mcp/http-status
```

It reports `running: false` unless you started the server in HTTP mode
(`serve-mcp --http`). Confirm the host/port match `MCP_HTTP_HOST` /
`MCP_HTTP_PORT` (defaults `127.0.0.1:8765`).

### MCP HTTP Returns 401 Unauthorized

If `MCP_AUTH_TOKEN` is set, HTTP clients must send
`Authorization: Bearer <token>`. Clear the variable to disable authentication,
or configure the matching token on the client.

### Inbox Ingestion Fails

`ingest_pdf` accepts either a local `path` or an `inbox_filename`. For the
filename form, the file must exist under the inbox folder (`INBOX_DIR`, default
`data/inbox/`). Use the `list_inbox` tool to see available files.

### stdio Logging

In stdio mode, stdout is the JSON-RPC channel. The server writes all
informational logging to stderr; do not expect logs on stdout.

### External Client (e.g. Claude Desktop) Shows "Server disconnected" / `ModuleNotFoundError`

If a desktop client's MCP log shows:

```text
Error while finding module specification for 'private_pageindex.cli'
(ModuleNotFoundError: No module named 'private_pageindex')
```

the package is not importable from the directory the client launches it in.
Running `serve-mcp` from the project root can hide this because the current
directory is added to the import path; external clients often launch from a
different working directory and do **not** reliably honor the config `cwd`
field. Fix it by installing the package into the venv so it resolves from any
directory:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Verify it resolves from an unrelated directory:

```powershell
cd C:\ ; & "D:\Projects\private-pageindex-rag\.venv\Scripts\python.exe" -c "import private_pageindex; print(private_pageindex.__file__)"
```

Because the launch cwd is unreliable, also pin absolute storage paths in the
client's MCP entry so it shares the same data as the web app. Example
`claude_desktop_config.json` entry:

```json
{
  "mcpServers": {
    "private-pageindex-rag": {
      "command": "D:\\Projects\\private-pageindex-rag\\.venv\\Scripts\\python.exe",
      "args": ["-m", "private_pageindex.cli", "serve-mcp"],
      "cwd": "D:\\Projects\\private-pageindex-rag",
      "env": {
        "DATA_DIR": "D:\\Projects\\private-pageindex-rag\\data",
        "INBOX_DIR": "D:\\Projects\\private-pageindex-rag\\data\\inbox"
      }
    }
  }
}
```

Fully quit the client (including any tray/background process) and relaunch so it
re-reads the config and restarts the server. Without absolute `DATA_DIR`, the
server resolves the relative default (`data/`) against the client's launch
directory and appears empty because it points at the wrong storage location.

## Check Ollama

The app expects Ollama at:

```text
http://localhost:11434
```

Check installed models:

```powershell
ollama list
```

Pull the default model if missing:

```powershell
ollama pull gemma4:e4b
```

Check the app status endpoint:

```text
http://127.0.0.1:8000/api/ollama-status
```

## PDF Upload Fails

Common causes:

- The file is not a `.pdf`.
- The PDF is scanned or image-only.
- The PDF is encrypted.
- Every page is empty after selectable-text extraction.

V1 does not support OCR. Use a selectable-text PDF for indexing.

## Messy Or Unstructured PDFs

The tree builder handles common messy-PDF patterns such as repeated numbering,
same-page subheadings, one-word structural headings, references sections,
glossaries, indexes, and blank pages. The generated tree JSON may include
`flags` metadata such as `is_blank` to make structural anomalies visible.

This is still best-effort text-PDF parsing. It does not perform OCR or layout
semantic analysis beyond the extracted text lines.

## Document Stuck In Processing

If the web server stops during indexing, the next app startup marks any `processing` documents as `failed` with this error:

```text
Indexing was interrupted by a server restart.
```

Re-upload the document after the server is running normally.

## Indexing Progress Does Not Move

The upload page polls:

```text
http://127.0.0.1:8000/api/documents/<doc_id>/status
```

If the card does not update, check the browser console and confirm the document
still has `status = processing` in `data/private_pageindex.db`. The progress is
stage-based, so long Ollama summarization can stay on `building tree` for a
while before moving to the next stage.

## Model Picker Is Empty

The model picker reads available local models from:

```text
http://127.0.0.1:8000/api/ollama-models
```

If it is empty, verify Ollama is running and `ollama list` shows at least one
model. Pull a model with:

```powershell
ollama pull gemma4:e4b
```

## Deleted Documents Leave Old Rows

Document deletion now removes document rows, nodes, chats, retrieval traces, the
uploaded PDF, extracted page text, and tree JSON. App startup also removes
orphaned chat and retrieval rows that may have been left by older versions or
manual database edits.

## Runtime Folders

These folders are generated locally and ignored by git:

```text
.venv/
data/
test_runtime/
__pycache__/
private_pageindex_rag.egg-info/
```

Do not commit these folders. Delete them only when you intentionally want to reset local environment, indexed documents, test artifacts, or build metadata.
