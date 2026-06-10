# Troubleshooting

## Run The Full Test Suite

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected current result: 116 passing tests.

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
