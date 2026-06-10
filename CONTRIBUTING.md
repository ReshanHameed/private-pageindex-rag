# Contributing to Private PageIndex RAG

Thank you for your interest in contributing to **Private PageIndex RAG**! We welcome contributions from developers of all skill levels to help improve the local indexing pipelines, spatial knowledge graphs, and RAG interfaces.

---

## 🔒 The Local-First Privacy Guarantee
This project is built under a strict design boundary: **no private data leaves the user's machine**. 
When contributing code, you must adhere to these invariants:
*   Do not introduce cloud inference providers (OpenAI, Anthropic, etc.) or hosted vector databases.
*   Do not connect to hosted PageIndex Cloud services.
*   All LLM interactions must route through the configured local Ollama endpoint (`http://localhost:11434` by default).
*   All PDF documents, extracted texts, and databases must reside locally within the configured `DATA_DIR` (default: `data/`).

---

## 🛠️ Development Setup

To make modifications, you will need to set up both the Python backend and Vite/React frontend environments.

### Prerequisites
*   **Python 3.13+**
*   **Node.js 18+** (with `npm`)
*   **Git**
*   **Ollama** (running locally with at least one model pulled, e.g., `gemma4:e4b`)

### 1. Backend Setup
1. Clone your fork of the repository and navigate to the project directory.
2. Initialize the Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e .[dev]
   ```
3. Copy the template settings file:
   ```powershell
   copy .env.example .env
   ```
4. Start the FastAPI backend server:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn private_pageindex.web.app:app --reload --host 127.0.0.1 --port 8000
   ```

### 2. Frontend Setup
1. Open a separate terminal, navigate to the `frontend/` directory, and install dependencies:
   ```powershell
   cd frontend
   npm install
   ```
2. Start the Vite development server:
   ```powershell
   npm run dev
   ```
3. Open your browser to **http://localhost:5173**. All API requests will be proxied automatically to the backend on port 8000.

---

## 🧪 Testing & Validation

Before submitting any pull requests, you must ensure that all code compiles, lints, and passes existing test suites.

### Backend Tests
The backend uses `pytest` for test automation. Run the full test suite (expecting 116 tests to pass):
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
If you modify tree-building schemas or storage layouts, write accompanying tests in the `tests/` directory.

### Frontend Linting & Compilation
Check the frontend codebase for TypeScript errors and ESLint rule compliance:
```powershell
cd frontend
npm run lint
```
Verify that the production compilation completes successfully without bundle errors:
```powershell
npm run build
```

---

## 📥 Submission Process

1. **Fork** the repository and create a descriptive feature branch (e.g., `feature/circular-layout-zoom`).
2. Implement your changes, following the existing module architecture.
3. Ensure all backend tests pass and the frontend compiles/lints cleanly.
4. **Commit** your changes with clear, descriptive commit messages.
5. Push your branch to your fork and submit a **Pull Request** to the main repository.

---

## 📚 Reference Documentation
For a deeper dive into the system modules, design aesthetics, and database schemas:
*   [README.md](file:///d:/Projects/private-pageindex-rag/README.md): Quick-start and CLI commands.
*   [docs/ARCHITECTURE.md](file:///d:/Projects/private-pageindex-rag/docs/ARCHITECTURE.md): System data flows and SQLite schemas.
*   [design.md](file:///d:/Projects/private-pageindex-rag/design.md): Typography, colors, and layout specs.
*   [docs/TROUBLESHOOTING.md](file:///d:/Projects/private-pageindex-rag/docs/TROUBLESHOOTING.md): Error recovery guides and environment fixes.
