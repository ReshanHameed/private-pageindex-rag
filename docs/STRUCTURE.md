# Project Structure

```text
private-pageindex-rag/
  .github/
    workflows/
      tests.yml
    ISSUE_TEMPLATE/
      bug_report.md
      feature_request.md
    PULL_REQUEST_TEMPLATE.md
  README.md
  pyproject.toml
  LICENSE
  CONTRIBUTING.md
  CODE_OF_CONDUCT.md
  SECURITY.md
  CHANGELOG.md
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  docs/
    ARCHITECTURE.md
    DESIGN.md
    PROJECT.md
    STRUCTURE.md
    TROUBLESHOOTING.md
    AGENT_MEMORY.md
  examples/
    test_document.pdf
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    components.json
    public/
      fonts/
      favicon.svg
      icons.svg
    src/
      App.tsx
      main.tsx
      index.css
      components/
      pages/
      lib/
      hooks/
  private_pageindex/
    config.py
    storage.py
    cli.py
    __main__.py
    indexing/
      entity_extraction.py
      heading_detection.py
      tree_builder.py
      tree_postprocessing.py
      tree_validation.py
    ingest/
      pdf_text.py
      pipeline.py
    llm/
      base.py
      ollama.py
    retrieval/
      answering.py
      tree_search.py
    web/
      app.py
  tests/
    test_*.py
```

## Source Folders

- `private_pageindex/` is the Python backend package.
- `frontend/` is the React SPA client application.
- `tests/` contains the backend automated test suite.
- `docs/` contains project documentation.
- `examples/` contains sample files for manual local checks.

## Runtime Folders

- `.venv/` is the local Python virtual environment.
- `frontend/node_modules/` is the local Node packages directory.
- `frontend/dist/` is the compiled production build of the frontend.
- `data/` is the local app database, uploaded PDFs, extracted pages, and trees.
- `test_runtime/` contains generated test artifacts.
- `private_pageindex_rag.egg-info/` is generated packaging metadata.
- `__pycache__/` folders are generated Python bytecode caches.

These runtime folders are intentionally ignored in `.gitignore`.
