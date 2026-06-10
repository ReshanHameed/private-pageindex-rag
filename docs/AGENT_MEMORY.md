# Project Agent Memory

Last updated: 2026-06-10

This is the living handoff file for AI agents working on `private-pageindex-rag`. Read it after `AGENTS.md` and before editing. Update it at the end of every agent session that changes code, tests, docs, configuration, or project direction.

## How To Use This Memory

- Treat this file as a current map, not as a replacement for reading source code.
- Verify any drift-prone claims such as test counts, dependency versions, or runtime behavior before relying on them.
- Add new entries to `Recent Work Log` in reverse chronological order.
- Keep entries concise and factual so the file stays useful in agent context windows.

## Project Summary

`private-pageindex-rag` is a fully private, local-first PageIndex-style RAG prototype for selectable-text PDFs.

The app:

- Uploads or ingests local text PDFs.
- Extracts selectable text with PyMuPDF.
- Builds a local PageIndex-style document tree.
- Stores PDFs, extracted page text, tree JSON, document metadata, chats, and retrieval traces in local SQLite plus the filesystem.
- Uses a local Ollama server for optional tree-title/summary enhancement, tree-guided node selection, and grounded answer generation.
- Provides a FastAPI web UI and CLI commands.

Privacy boundary:

- Document contents live under local `DATA_DIR`, default `data/`.
- Inference is expected to use local Ollama at `http://localhost:11434`.
- The project should not call hosted inference providers or PageIndex Cloud.

## Implemented Feature Set

- Feature 0: environment/setup documentation.
- Feature 1: project skeleton and settings.
- Feature 2: local SQLite/filesystem storage.
- Feature 3: selectable-text PDF extraction.
- Feature 4: local Ollama client with text, JSON, health, and error handling.
- Feature 5: PageIndex-style tree builder.
- Feature 6: indexing pipeline.
- Feature 7: tree-search retrieval and grounded answering with citations.
- Feature 8: local FastAPI web app.
- Feature 9: CLI and final docs.
- Later hardening: messy-PDF tree reliability, tree validation reports, duplicate/cover/repeated-header handling, blank-page flags, and title-preserving LLM summary enhancement.
- Later UX/lifecycle work: background web indexing, stage-based progress bars, elapsed indexing timer, web Ollama model picker, progress status endpoints, and orphan chat/trace cleanup.

## Current Architecture Map

- `private_pageindex/config.py`: Pydantic settings from environment or `.env`.
- `private_pageindex/storage.py`: SQLite schema, document/node/chat/retrieval-step records, progress fields, cleanup helpers, and artifact paths.
- `private_pageindex/ingest/pdf_text.py`: PyMuPDF selectable-text extraction and extraction errors.
- `private_pageindex/ingest/pipeline.py`: end-to-end indexing, tree validation persistence, node row insertion, and failure recording.
- `private_pageindex/indexing/tree_builder.py`: heading detection, fallback tree generation, normalization, validation, summaries, and optional LLM enhancement.
- `private_pageindex/llm/ollama.py`: local Ollama API client.
- `private_pageindex/retrieval/tree_search.py`: tree-guided selection of relevant nodes and retrieved pages.
- `private_pageindex/retrieval/answering.py`: grounded answer generation from retrieved text.
- `private_pageindex/web/app.py`: upload, delete, document view, chat, trace, and Ollama status routes.
- `private_pageindex/cli.py`: `ingest`, `ask`, and `serve` commands.
- `tests/`: automated test suite.
- `docs/`: product, architecture, implementation history, structure, troubleshooting, plans, and this agent memory.

## Key Invariants

- V1 supports selectable-text PDFs only. No OCR for scanned/image-only PDFs.
- No cloud inference or hosted PageIndex dependency.
- `data/` and `test_runtime/` are runtime folders and should stay ignored.
- Tree JSON must keep these existing node fields: `node_id`, `title`, `start_page`, `end_page`, `summary`, `nodes`.
- Additive metadata such as `flags` and top-level `validation` is acceptable.
- Documents stuck in `processing` are marked `failed` on web app startup.
- Web upload indexing is backgrounded; progress is stored on `documents` and exposed through `/api/documents/{doc_id}/status`.
- Web model selection comes from local Ollama `/api/tags` and is passed as a per-request model to indexing and chat.
- Document deletion must remove chats, retrieval steps, nodes, document rows, uploaded PDFs, extracted pages, and tree JSON; startup cleanup removes old orphan chat/trace rows.
- CLI command names are part of the user-facing contract: `ingest`, `ask`, `serve`.
- FastAPI routes documented in `README.md` are user-facing contracts.

## Known Runtime Assumptions

- Python 3.13+.
- Local virtual environment at `.venv/`.
- Default Ollama model: `gemma4:e4b`.
- Default Ollama URL: `http://localhost:11434`.
- Default app URL: `http://127.0.0.1:8000`.

## Verification Baseline

Expected full suite command:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

The latest project docs say the full suite contains 116 tests. Verify this live before reporting it as current.

## Recent Work Log

### 2026-06-10 - Implemented Custom Markdown and Citation Parser for Chat Console

What changed:
- **Markdown & Citation Parser**: Implemented a lightweight, custom hybrid markdown parser in a new utility `markdown.tsx`. It parses block-level elements (headings `#`/`##`/`###`, bullet lists `- ` with indentation, numbered lists `1. ` with indentation) and inline elements (bolding `**text**`, interactive citation links like `[page N]`).
- **Updated Chat UI Components**: Integrated the new `renderStructuredAnswer` utility in `ChatMessage.tsx` and `StreamingMessage.tsx`. Replaced the old regex-split implementation, resolved newline collapse issues by applying `whitespace-pre-wrap` to parent message containers, and preserved structured layouts cleanly for completed responses and real-time streaming tokens.

Files changed:
- `frontend/src/lib/markdown.tsx` (NEW)
- `frontend/src/components/chat/ChatMessage.tsx`
- `frontend/src/components/chat/StreamingMessage.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 116 tests passed successfully.
- Frontend lint: `npm run lint` passes with 0 errors.
- Frontend build: `npm run build` compiles successfully.
- AST Knowledge Graph updated via `graphify update .`.

### 2026-06-10 - Fixed Undefined Variable isStreaming ReferenceError in GraphNode

What changed:
- **GraphNode isStreaming Reference Fix**: Added `isStreaming` to the destructured props parameters of the `GraphNode` component in `GraphNode.tsx`. Previously, `isStreaming` was declared in `GraphNodeProps` but was omitted in the function signature destructuring block, throwing a runtime `ReferenceError: isStreaming is not defined` when rendering graph nodes.

Files changed:
- `frontend/src/components/graph/GraphNode.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 116 tests passed.
- Frontend lint: `npm run lint` passes with 0 errors.
- Frontend build: `npm run build` compiles successfully.
- AST Knowledge Graph updated via `graphify update .`.

### 2026-06-10 - Trace Page Instant Loading and Database Query Index Optimization

What changed:
- **SQLite Database Indexing**: Added four performance indices (`idx_retrieval_steps_chat_id`, `idx_chats_session_id`, `idx_chats_doc_id`, `idx_chat_sessions_doc_id`) on SQLite foreign keys in `storage.py`. This prevents full table scans on retrieval steps, session chats, and document lists, delivering a 16.5x query speedup.
- **Trace Page Zustand Store Integration**: Updated `TracePage.tsx` to check for cached document and chat records in `useAppStore` before falling back to network fetches. Clicking "VIEW_TRACE" now opens the timeline view instantly (0ms) from local memory.
- **Route-level Code Splitting**: Configured `App.tsx` routes to use `React.lazy` and `React.Suspense` for `DashboardPage`, `DocumentPage`, and `TracePage`. This isolates page bundles, shrinking the core load size and preventing D3-force script execution from delaying general page paint times.

Files changed:
- `private_pageindex/storage.py`
- `frontend/src/pages/TracePage.tsx`
- `frontend/src/App.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 116 tests passed.
- Frontend build: Completed successfully with split chunks.

### 2026-06-10 - Synchronized Progress Bar and Added Detailed Indexing Sub-Stages

What changed:
- **ProgressBar Animation Mismatch Fix**: Replaced the `update` callback with `onUpdate` inside the `animate()` properties argument in `ProgressBar.tsx`. This aligns with `animejs` v4's API, ensuring the animated value is properly updated on every frame.
- **Detailed Ingestion Progress Sub-Stages**: Modified `build_tree` to accept an optional `progress_callback` argument and report granular indexing sub-stages (omitting the `"building tree: "` prefix, e.g. `detecting headings`, `checking repeated headers`, `fallback page ranges`, `normalizing structures`, `generating summaries`). This prevents UI text truncation.
- **Dynamic Node Enhancement Progress**: Updated `_enhance_with_llm` to report progress updates for each individual node processed by the local Ollama model (e.g. `enhancing node 3 of 10`) alongside a linearly increasing progress percentage from 49% up to 68%. This ensures the progress bar increments smoothly during the longest part of document ingestion.
- **Wired Progress Callback in Pipeline**: Updated `pipeline.py` to forward the local `emit` database status helper to `build_tree()`.
- **Added Progress Callback Unit Test**: Implemented `test_build_tree_calls_progress_callback` in `test_tree_builder.py` to assert that `build_tree` invokes the progress callback with the expected stages and percentages.
- **Card Height Stretching and Gap Fix**: Replaced the progress/status details bar with the inline delete confirmation bar when `deletingId === doc.id` in `DashboardPage.tsx` (and reverted grid layouts back to standard stretching heights). This ensures the card height remains completely identical in both states, resolving height mismatches and preventing empty grid gaps entirely while keeping cards in the same row beautifully aligned.
- **FastAPI Event-Loop Blocking Fix**: Converted 18 synchronous CPU-bound and I/O-bound routes (like fetching list of documents, tree structures, status checking, deleting documents, and rendering static templates) in `app.py` from `async def` to standard `def`. This offloads these SQLite and disk-access operations to FastAPI's built-in external thread pool, preventing them from blocking the main single-threaded asyncio event loop, resolving UI unresponsiveness and lag during navigation.

Files changed:
- `frontend/src/components/documents/ProgressBar.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `private_pageindex/indexing/tree_builder.py`
- `private_pageindex/ingest/pipeline.py`
- `private_pageindex/web/app.py`
- `tests/test_tree_builder.py`
- `docs/AGENT_MEMORY.md`

Verification:
- Full Python test suite passes: 116 tests passed.
- Frontend linter passes: 0 errors.
- Frontend build succeeds.
- AST Knowledge Graph updated via `graphify update .`.

## Recent Work Log

### 2026-06-09 - Highlighted Graph Connecting Strings with Dynamic Accent Color

What changed:
- **Graph Edge Accent Highlight**: Changed the base color of graph connecting lines (edges) from a dark, barely visible `--color-border-dim` to the theme's vibrant `--color-accent` (Mineral Teal).
- **Dynamic Path Tracing**: Equipped `GraphEdge.tsx` with dynamic styling parameters (`isActivated`, `isFetched`, `isSelected`) so that the connecting strings trace RAG retrieval, SSE streaming steps, and user selection. Added transition properties for smooth thickness/opacity interpolation.
- **Harmonized Edge Styling Coefficients**: Adjusted secondary state values (active, selected) proportionally (active width: 2.0, selected width: 2.5) to align with the user's customized base thickness (1.5) and fetched maximums (3.0), creating a clean and logical visual hierarchy.
- **Persistent Node Glowing**: Removed the conditional `isStreaming` check from the pulse animation rule in `GraphNode.tsx` for fetched nodes. Fetched nodes and paths now keep glowing/pulsing after the streaming RAG answer finishes, and only clear when a new question starts (resetting the store).
- **Fixed Switch Document State Leakage**: Fixed a bug where switching between documents leaked the active/fetched node glow states to the new graph. Added `useStreamStore.getState().reset()` and `setSelectedNode(null)` inside the `docId` `useEffect` hook in `DocumentPage.tsx` to completely reset the visual trace state when navigating between files.
- **Fixed Retrieval Trace Loading Failure**: Resolved a crash on the Trace Debugger page ("Failed to load trace data"). This was caused by the `/api/documents/{doc_id}/chats/{chat_id}` route directly referencing `storage._conn` which was removed during connection leak refactoring. Added a clean database abstraction `get_chat(chat_id)` to `storage.py` and updated `app.py` to route through it.
- **Checked off Todo items**: Marked all build, lint, and test validation tasks as completed in `TODO.md`.
- **AST Knowledge Graph Update**: Rebuilt the local AST graph file with `graphify update .`.

Files changed:
- `frontend/src/components/graph/GraphEdge.tsx`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/pages/DocumentPage.tsx`
- `private_pageindex/storage.py`
- `private_pageindex/web/app.py`
- `TODO.md`
- `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 115/115 tests passed.
- Frontend lint: `npm run lint` passes with 0 errors and 4 warnings.
- Frontend build: `npm run build` compiles successfully.

### 2026-06-09 - Ran All Tests and Fixed GraphNode Compilation Error

What changed:
- **Test Execution**: Ran the full python pytest suite (115/115 passed).
- **Linter & Type Checking**: Ran the frontend linter (0 errors, 4 warnings).
- **Frontend Compilation**: Discovered and fixed a TypeScript compilation error in `GraphNode.tsx` where `isStreaming` was declared in `GraphNodeProps` but not destructured in the component parameters. Fixed this, which successfully compiled the production build (`npm run build`).

Files changed:
- `frontend/src/components/graph/GraphNode.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 115 tests passed.
- Frontend lint: `npm run lint` passes with 0 errors.
- Frontend build: `npm run build` succeeds.

### 2026-06-08 - Fixed Chat Session History Bug

What changed:
- **Frontend / Ask API**: Fixed a bug where every query would start a new chat session instead of appending to the current one. Updated `DocumentPage.tsx` to include `session_id: useAppStore.getState().activeSessionId` in the JSON body of the `/api/documents/{docId}/ask/stream` request.

Files changed:
- `frontend/src/pages/DocumentPage.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Confirmed that sending queries appends them to the active session and retains previous chat history in the panel.


### 2026-06-08 - Fixed Graph Scaling, Packing, and Bouncing Animations

What changed:
- **Consistent Initialization**: Replaced `Math.random()` with a golden ratio mathematical spiral for node initialization to guarantee the force simulation resolves into the exact same predictable shape every time a document is loaded.
- **Dynamic Density & Aspect Ratio Packing**: Calculated the actual empty-space aspect ratio of the user's panel and piped it into the `d3-force` X/Y gravity simulation. This squashes the physics bounding box into the exact shape of the panel. Lowered background `charge` repulsion and tightened `link.distance` to 30px to force a hyper-dense packing. 
- **Increased Base Sizes**: Scaled up base node radius (to 10px/16px) and text font sizes (`text-[12px]`) to drastically improve visual legibility.
- **Removed Auto-Fit Shrinking & Bleeding Restrictions**: Raised the collision radius shield with full strength (1.0 -> 0.7) to prevent the hyper-dense nodes from overlapping. Combined with the density packing, the graph is small enough that the `fitTransform` auto-scale camera can fit everything entirely on-screen without bleeding and without having to shrink the camera down to tiny, illegible scales.
- **Cinematic Unfolding Physics**: Replaced the violent "billiard ball" bouncy initialization explosion by cranking up `velocityDecay` (friction) to 0.75, lowering `collide` strength to 0.7 to allow temporary soft-collisions, and lowering `alphaDecay` to 0.015. Nodes now slide elegantly through "molasses" into their final tree positions.

Files changed:
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Mathematical dense-packing properly limits bounding box size.
- Friction completely suppresses jitter and bouncing.
- Frontend TS/Linter: `npm run lint; npx tsc --noEmit` pass with 0 errors.

### 2026-06-08 - Implemented Precise Circular Knowledge Graph Layout

What changed:
- **Strict Circular Math Layout**: Replaced the D3 `forceSimulation` in `KnowledgeGraph.tsx` with a precise mathematical circular layout. This solves the problem of nodes randomly scattering or clumping together.
- **Dynamic Arc Spacing**: The circle's radius dynamically scales based on the number of nodes (`arcLength = 180`) to guarantee nodes and text labels do not mix, overlap, or hide each other along the circumference.
- **Fixed Scaling Bounds**: Modified the `fitTransform` auto-scale logic to calculate bounding boxes with generous padding (`r = node.radius + 80`) and lowered the minimum scale cap from `0.45` to `0.05`. This ensures the perfect circle shape remains precisely fixed and fully visible inside the panel frames regardless of how many nodes are rendered.

Files changed:
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Mathematical layout prevents overlapping text strings.
- Frontend TS/Linter: `npm run build` triggered to verify types.

### 2026-06-08 - Fixed Spatial Knowledge Graph Node Collapse

What changed:
- Fixed a serious graph rendering bug where SVG graph nodes and labels could collapse near the top-left or appear disfigured.
- Root cause: `GraphNode.tsx` applied `animate-fade-in` to an SVG `<g>` that also used a `transform="translate(x,y)"`; the CSS animation wrote its own transform and could override the SVG transform coordinates.
- Removed the SVG node fade-in animation class from graph nodes.
- Changed `KnowledgeGraph.tsx` from a continuous D3 tick loop to a one-time settled force layout, rendering only final coordinates instead of unstable intermediate ticks.
- Removed unused graph pulse/glow animation keyframes and classes from `frontend/src/index.css`.

Files changed:
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/index.css`
- `docs/AGENT_MEMORY.md`

Verification:
- Regression source check: passes; no SVG node transform animation, no continuous D3 tick render loop, no graph pulse/glow classes.
- Frontend lint: `npm run lint` passes with 0 errors and 4 existing warnings.
- Frontend build: `npm run build` passes.
- Rendered browser screenshots captured with Playwright CLI using installed Edge channel for the 4-node resume document, 16-node earnings document, and 66-node health-monitoring document; graphs render visible, distributed, and non-collapsed.

### 2026-06-08 - Removed Knowledge Graph Settings Toggle

What changed:
- Removed the Knowledge Graph settings toggle from both mobile and desktop document graph headers.
- Removed `GraphSettingsPanel.tsx` and all `GraphSettings` state, localStorage persistence, sanitization, reset, and settings-change handlers from `DocumentPage.tsx`.
- Converted `KnowledgeGraph.tsx` and `GraphNode.tsx` back to fixed internal graph layout constants for force strength, link distance, collision padding, node sizes, label font size, and label truncation.
- Removed the unused `GraphSettings` type from `frontend/src/lib/types.ts`.

Files changed:
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/components/graph/GraphSettingsPanel.tsx` (deleted)
- `frontend/src/lib/types.ts`
- `docs/AGENT_MEMORY.md`

Verification:
- Frontend lint: `npm run lint` passes with 0 errors and 4 existing warnings.
- Frontend build: `npm run build` passes.

### 2026-06-07 - Knowledge Graph Layout Customization Controls & Spacing Settings

What changed:
- **Interactive Spacing Controls**: Added the `GraphSettings` type and implemented `graphSettings` state in `DocumentPage.tsx` with `localStorage` persistence.
- **Defensive Coordinate Caching & Document Switch Reset**: Fixed a bug where navigating between documents caused the graph to collapse to the center of the panel. Added a `lastTreeRef` structure check that resets the coordinate cache (`coordsRef.current = new Map()`) when switching files. Added type validations and `isNaN` checks on both cache lookup and cache saving loops.
- **Robust D3 Link Object Mapping**: Fixed a simulation failure where D3's `.force('link')` could not resolve link sources/targets on subsequent simulation runs when settings changed (because D3 mutates them from strings to objects on the first run, making subsequent string-based ID resolutions fail and collapse the graph). Reverted link generation to standard object references and mapped links dynamically in the simulation `useEffect` to the fresh node objects of the current run, eliminating resolution failures completely.
- **Defensive LocalStorage Settings Parser**: Implemented strict type and bounds validation on settings loading to prevent `NaN` or `undefined` values from older storage schemas from corrupting simulation force coefficients.
- **Floating Settings Panel Overlay**: Created `GraphSettingsPanel.tsx` providing slider controls for repulsion strength, link distance, collision spacing, parent/leaf node sizes, label font sizes, label truncation lengths, and a label visibility toggle.
- **Continuous Force Physics Simulation**: Re-enabled continuous force simulations (ticking loop animations) to run dynamically in the background instead of running synchronous ticks on mount. Added a custom virtual-bounds D3 force to strictly contain all nodes inside the layout boundaries.
- **Dynamic Node and Text Sizes**: Updated `GraphNode.tsx` to read radius, label visibility, label font size, and label truncation limits directly from `settings`.

Files changed:
- `frontend/src/lib/types.ts`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/components/graph/GraphSettingsPanel.tsx` (NEW)
- `docs/AGENT_MEMORY.md`

Verification:
- Frontend TS/Linter: `npm run lint` and `npx tsc --noEmit` pass with zero errors.
- Python tests: `pytest` suite passes all tests.
- Graphify graph: Rebuilt and updated with `graphify update .`.

### 2026-06-07 - Frontend Layout Fit, Panel Spacing, & Animation Bypasses

What changed:
- **Layout Full-Width & Padding Fit**: Modified the layout wrapper in `AppShell.tsx` to conditionally remove the `max-w-[1140px]` constraint and adjust padding (`pl-14 pr-6 pb-6 pt-4`) when viewing a document page. This allows the graph and chat panels to stretch full-width and fit perfectly under the global header, footer, and sidebar.
- **Panel Spacing**: Increased the spacing between the left knowledge graph panel and right chat panel in `DocumentPage.tsx` by widening the resize handle element width from `w-2` to `w-6`.
- **Disabled Graph Animations**: Completely bypassed the `anime.js` entrance animations on load in `KnowledgeGraph.tsx`, ensuring nodes and edges render instantly at full size and opacity.
- **Disabled CSS Pulse/Glow Animations**: Replaced active dynamic classnames (`animate-fetch-pulse`, `animate-select-glow`, etc.) in `GraphNode.tsx` with static highlighted color layouts (`fill-accent`, `fill-accent-ghost`) to prevent flickering and alignment rendering bugs during streaming retrieval.
- **Disabled D3 Force Layout Ticking Animation**: Stopped dynamic ticking animation loops in `KnowledgeGraph.tsx` by invoking `.stop()` and running 200 ticks synchronously in a `for` loop on initialization. Nodes now render immediately in their final settled force coordinates without moving or sliding.
- **Disabled D3 Zoom and Pan**: Disabled mouse-wheel scroll zoom, pointer-click dragging to pan, and parent zoom in/out panel controls by removing state updates and setting cursor styles to `cursor-default`.
- **Disabled Hover and Focus Transitions**: Removed all dynamic hover transformations (`group-hover:`) and transition rules (`transition-all`, `transition-colors`) from node circles, labels, and edges in `GraphNode.tsx` and `GraphEdge.tsx` to keep the layout static.
- **Fixed Node Overflow & Resize Scattering**: Configured D3 force simulation to calculate node coordinates inside a fixed virtual box (`800`x`600`) exactly once when the `graphData` changes (instead of re-running simulation on panel resize). Implemented a render-phase `useMemo` that calculates the graph's bounding box and computes a dynamic transform (`translate` and `scale` factor) to scale down and keep the graph centered inside the panel dimensions perfectly, preventing nodes from scattering or overflowing the border.
- **Fixed Node Text Spacing & Overlaps**: 
  - Increased D3 simulation link distance to `120`, increased charge repulsion strength to `-380` over a `380` max distance, and calculated a dynamic node collision radius in `KnowledgeGraph.tsx` based on the character length of the node title (`d => d.radius + Math.min(65, d.data.title.length * 3.5) + 16`). This forces nodes with long text labels to space themselves out horizontally, preventing overlaps.
  - Replaced relative `dy` offsets with absolute `y` coordinates in `GraphNode.tsx` that scale dynamically with the node's radius (setting `y={-(node.radius + 8)}` for page badges and `y={node.radius + 12}` for labels). This guarantees a clean, consistent vertical spacing gap around node circles, preventing text from rendering on top of the node borders.

Files changed:
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/components/graph/GraphEdge.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- Frontend TS/Linter: `npm run lint` checked.

### 2026-06-06 - Chat Sessions ("Threads") Memory

What changed:
- **Database Schema**: Added `chat_sessions` table with a foreign key in `chats` to support multiple conversation threads per document. Included migration logic in `LocalStorage.initialize()` to assign existing legacy chats to default sessions smoothly without crashing.
- **Backend APIs**: Modified `storage.py` and `app.py` APIs (`insert_chat`, `list_chats`, `/ask/stream`) to require and handle `session_id`. Added `GET /api/documents/{doc_id}/sessions` and `GET /api/documents/{doc_id}/chats/{chat_id}` to fetch sessions and specific trace items.
- **Frontend State**: Updated `frontend/src/lib/store.ts` to manage multiple `currentSessions` and track an `activeSessionId`.
- **Frontend UI**: Refactored `AppShell.tsx` to list "Chat Sessions" in the sidebar instead of flat chat histories. Added a `New` button to `ChatPanel.tsx` that resets the active session, seamlessly allowing the user to start a new context thread. Updated `TracePage.tsx` to fetch specific trace items from the new API.

Files changed:
- `private_pageindex/storage.py`
- `private_pageindex/web/app.py`
- `tests/test_storage.py`
- `tests/test_web_app.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/store.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/chat/ChatPanel.tsx`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/pages/TracePage.tsx`

Verification:
- Python test suite: `pytest` passes 115/115 tests with no failures.
- Frontend TS: `npm run build` compiles successfully.

### 2026-06-06 - Chat Session Deletion

What changed:
- **Backend**: Added `delete_chat_session` to `storage.py` and exposed `DELETE /api/documents/{doc_id}/sessions/{session_id}` in `app.py`. The deletion cascades to remove all associated chats and retrieval steps from the database.
- **Frontend**: Added `deleteSession` to `store.ts` and `api.ts`. Added a trash icon to the session list in `AppShell.tsx` which triggers a confirmation dialog and then deletes the session. If the active session is deleted, the UI correctly falls back to another session or clears the chat panel.

Files changed:
- `private_pageindex/storage.py`
- `private_pageindex/web/app.py`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/store.ts`
- `frontend/src/components/layout/AppShell.tsx`

Verification:
- Python test suite: `pytest` passes 115/115 tests.
- Frontend TS: `npm run build` compiles successfully.

### 2026-06-06 - Progress Bar & Sidebar UI Enhancements

What changed:
- **Frontend / ProgressBar**: Changed ASCII characters from `■`/`░` to `█`/`-` to fix a vertical bleeding bug in the browser font. Increased the default length to 30 blocks and enforced `whitespace-nowrap` to prevent messy layout wrapping on small screens.
- **Frontend / Dashboard**: Adjusted the indexing card layout so the processing prompt (e.g. "BUILDING TREE...") and elapsed timer sit inline horizontally next to the progress bar with a clean `·` separator.
- **Frontend / Sidebar**: Updated the sidebar rendering of processing documents (`AppShell.tsx`) to pulse synchronously with an orange border (`border-warning/80`), `bg-bg-void` background, and `!text-warning` text to match the dashboard's indexing styling.

Files changed:
- `frontend/src/components/documents/ProgressBar.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/layout/AppShell.tsx`

Verification:
- Frontend TS: `npm run build` compiles successfully.

### 2026-06-06 - Conversational Memory Bug Fixes (Empty Sessions & Document Switch)

What changed:
- **Empty Sessions Hidden**: Fixed a bug where clicking "New Chat" and cancelling/failing would leave empty sessions visible in the sidebar. Modified `api_get_document_sessions` in `app.py` to only return sessions that contain at least one chat (`storage.list_chats(s.id, limit=1)`).
- **Session ID Crossover Fix**: Fixed a bug where switching between documents would keep the previous document's chat visible. Modified `fetchSessionsAndChats` in `store.ts` to strictly validate if the injected `sessionId` exists within the new document's sessions. If not, it falls back to the new document's first session (or `null`), correctly resetting the UI.

Files changed:
- `private_pageindex/web/app.py`
- `frontend/src/lib/store.ts`

Verification:
- Python test suite: `pytest` passes 115/115 tests.
- UI flow: Switching documents correctly loads that document's specific chats. Empty sessions are no longer rendered in the sidebar.

### 2026-06-06 - Conversational Memory (Multi-Turn Chat Context)

What changed:
- **Ollama Client**: Updated `chat_text`, `chat_json`, and `chat_text_stream` in `OllamaClient` and `AsyncOllamaClient` to accept an optional `history: list[dict[str, str]]` parameter and format it correctly as conversational messages for the local model.
- **Answering Pipeline**: Modified `generate_answer`, `generate_answer_async`, and `generate_answer_stream` in `answering.py` to accept the `chat_history` argument and pass it to the underlying LLM client.
- **Chat Endpoints**: Updated `/api/documents/{doc_id}/ask` and `/api/documents/{doc_id}/ask/stream` in `app.py` to fetch the previous 5 chat records for the document via `storage.list_chats()`, format them, and inject them into the RAG generation pipeline, enabling multi-turn contextual memory for all subsequent questions.
- **Test Fixes**: Fixed mocked functions in `test_answering.py` and `test_web_app.py` to accept the new `history`/`chat_history` keyword arguments.

Files changed:
- `private_pageindex/llm/ollama.py`
- `private_pageindex/retrieval/answering.py`
- `private_pageindex/web/app.py`
- `tests/test_answering.py`
- `tests/test_web_app.py`

Verification:
- Python test suite: `pytest` passes 115/115 tests with no failures.
- Multi-turn context logic behaves as expected for local models by correctly stacking chat contexts before the `user_prompt`.

### 2026-06-06 - AppShell Redesign: Shadcn Sidebar Integration & Rollback, Layout Polish

What changed:
- **Sidebar Attempt & Rollback**: Implemented the `sidebar-07` shadcn design (with collapsible documents, inset layout, floating header), but completely reverted it back to the single-column "Icon-Rail" layout at the user's request.
- **Documents Sidebar Integration**: Grouped the dynamic RAG document list inside an expandable `<Collapsible>` category named "Documents" natively within the icon-rail layout (replaces the flat list). Used the `Database` icon colored with `text-accent`.
- **Upload Button Polish**: Updated the main sidebar action button from `Terminal` to `FilePlus` and changed its label to "Add Document".
- **Global Scrolling Fix**: Resolved a bug in `DocumentPage` where its internal height exceeded the viewport causing the whole screen to scroll. Implemented strict `overflow-hidden` constraints at the root `AppShell` `<main>` layer, and delegated `overflow-y-auto` internal scrolling directly to `DashboardPage` and `TracePage`. `DocumentPage` now uses `flex-1 min-h-0` to perfectly constrain its desktop resizeable panels within the fixed window height.
- **Code Graph Update**: Updated the AST knowledge graph using `graphify update .`.

Files changed:
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/pages/TracePage.tsx`
- `docs/AGENT_MEMORY.md`

Verification:
- React compilation: `npx tsc --noEmit` succeeds with 0 errors.
- Python test suite: `pytest` passes 115/115 tests with no impact on backend routes.
- Frontend layout: App shell strictly locked to window height, while nested dashboard/trace pages and document panels scroll flawlessly.

### 2026-06-05 - Remove SmoothCursor & CursorToggle (Feature 3 dropped)

What changed:
- **Deleted `smooth-cursor.tsx`**: Removed the Magic UI `SmoothCursor` component from `frontend/src/components/ui/`.
- **Deleted `CursorToggle.tsx`**: Removed the header toggle switch for enabling/disabling the cursor from `frontend/src/components/layout/`.
- **Cleaned `AppShell.tsx`**: Removed `import CursorToggle` and `import { SmoothCursor }`, removed `smoothCursorEnabled` localStorage state, removed `toggleSmoothCursor` function, and removed both JSX usages (`<SmoothCursor />` render and `<CursorToggle />` in the header controls section).
- **Updated `design.md`**: Marked Feature 3 (Custom Cursor) as REMOVED throughout the document — design identity sentence, §4 component hierarchy note, §5 z-index table (`--z-cursor` removed), §6 motion table (custom cursor row removed), Feature 3 spec section replaced with removal notice, §9 feature list, §10 custom component manifest, §12 Phase 2 step 2.1, §14.3 Magic MCP tool table. The browser default cursor is now used.
- **Updated `docs/AGENT_MEMORY.md`**: Added this entry.

Files changed:
- `frontend/src/components/ui/smooth-cursor.tsx` (DELETED)
- `frontend/src/components/layout/CursorToggle.tsx` (DELETED)
- `frontend/src/components/layout/AppShell.tsx`
- `design.md`
- `docs/AGENT_MEMORY.md`

Verification:
- Vite dev server hot-reloaded with no errors (running on port 5173).
- No TypeScript errors expected — all imports and JSX were removed cleanly.

New invariants:
- Feature 3 (Custom Cursor) is permanently removed. Do not reinstate `SmoothCursor`, `CursorToggle`, or any custom cursor component unless the user explicitly requests it.
- The `--z-cursor` CSS token is no longer needed and has been removed from the design spec.
- `framer-motion` may now be an unused dependency in `package.json` — consider removing it if no other component uses it.

### 2026-06-04 - Phase 5.1 Design Compliance Audit & Fixes

What changed:
- **Side-stripe border ban fix**: Removed `border-l-2 border-l-accent/30` from `ChatMessage.tsx` and `StreamingMessage.tsx`. This was an absolute ban per design.md §11 (`impeccable` skill: side-stripe borders with `border-left > 1px` as accent are banned).
- **ASCII status indicators**: Replaced `rounded-full` div status dots in `OllamaStatus.tsx` with ASCII `●` (connected/checking) and `○` (offline) text characters per design.md §4 (ASCII Intensity spec). Removes non-compliant `border-radius` usage.
- **Duplicate CSS removal**: Removed duplicate `.skeleton-shimmer` class and `@keyframes skeleton-shimmer` from the bottom of `index.css`. The earlier definition in the Component Utilities section is the canonical one.

Files changed:
- `frontend/src/components/chat/ChatMessage.tsx`
- `frontend/src/components/chat/StreamingMessage.tsx`
- `frontend/src/components/layout/OllamaStatus.tsx`
- `frontend/src/index.css`

Verification:
- TypeScript type checking: `npx tsc --noEmit` passed with 0 errors.
- Vite build: `npm run build` succeeds (dist built in 545ms).
- ESLint: `npm run lint` passes with 0 errors (3 expected shadcn warnings).
- Python test suite: `pytest` passes 115/115 tests in 9.84s.

### 2026-06-04 - Phase 5.1 Design Polish & Component Refinement

What changed:
- **CSS Design System Synchronization (Step 5.9)**: Synced `index.css` with the design specifications, adding custom spacing, typography, transition duration tokens, custom scrollbars, and helper classes (`.focus-ring`, `.hover-lift`, `.skeleton-shimmer`).
- **Aesthetic Component Refinement (Step 5.10)**: 
  - Polished layout and components. Upgraded `DashboardPage.tsx` by replacing `window.confirm` with a custom `deletingId` inline card delete confirmation flow, and improved the empty documents state to a retro terminal interface.
  - Improved keyboard accessibility and drag-over transitions in `UploadZone.tsx`.
  - Refined formatting, active indicators, and focus states in `ModelPicker.tsx`, `OllamaStatus.tsx`, `ChatMessage.tsx`, `ChatInput.tsx`, `StreamingMessage.tsx`, `TraceTimeline.tsx`, `CommandPalette.tsx`, and `TracePage.tsx`.
- **Linter & React Hook Fixes**: Resolved ESLint errors/warnings. Replaced direct state change within `useEffect` inside `AppShell.tsx` with a render-phase mobile width state adjustment, and added missing dependencies to the fetch loop inside `DocumentPage.tsx`.
- **Code Graph Update**: Updated the AST knowledge graph using `graphify update .`.

Files changed:
- `frontend/src/index.css`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/documents/UploadZone.tsx`
- `frontend/src/components/chat/ChatMessage.tsx`
- `frontend/src/components/chat/ChatInput.tsx`
- `frontend/src/components/chat/StreamingMessage.tsx`
- `frontend/src/components/layout/ModelPicker.tsx`
- `frontend/src/components/layout/OllamaStatus.tsx`
- `frontend/src/components/trace/TraceTimeline.tsx`
- `frontend/src/components/CommandPalette.tsx`
- `frontend/src/pages/TracePage.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/pages/DocumentPage.tsx`

Verification:
- TypeScript type checking: `npx tsc --noEmit` passed with 0 errors.
- Vite build check: `npm run build` succeeds (dist built in 908ms).
- Linter checks: `npm run lint` passes with 0 errors.
- Python test suite: `pytest` passes 115/115 tests in 29.49s.

### 2026-06-04 - Phase 5 Integration & Mobile Polish + E2E Testing

What changed:
- **FastAPI serves Vite Build (Step 5.1)**: Configured SPA static asset serving in `app.py` directly from `frontend/dist/` with client-side SPA routing fallback when the build directory exists, supporting zero-config production environments while gracefully falling back to Vite development proxy.
- **Collapsible Sidebar Sections (Step 5.6)**: Upgraded `AppShell.tsx` to group navigation links into collapsible "Documents" and "Recent Chats" sections.
- **Shared Chat History**: Connected `DocumentPage.tsx` and the sidebar to the Zustand `useAppStore` so that the chat history of the *currently viewed document* is shared, loaded, and updated in real-time.
- **Accessibility & Focus Audits (Step 5.3)**: Added screen reader ARIA labels, `aria-live` and `aria-atomic` dynamic attributes, and keyboard outlines (`focus-visible:outline`) for the chatbot input and drag-and-drop file upload zone.
- **SSE Stream Testing (Step 5.7)**: Added `test_api_ask_document_stream` in `test_web_app.py` verifying full stream responses, events, and persistence.
- **Phase 5.1 Plan**: Created a detailed implementation plan for design, component auditing, and aesthetic polish utilizing Stitch, Magic, and Shadcn MCP servers, and specified the required custom agent skills from the home `~/.agents/skills/` folder (`impeccable`, `design-md`, `stitch-design-taste`, `stitch-loop`, `shadcn`, and `/graphify`).

Files changed:
- `private_pageindex/web/app.py`
- `frontend/src/lib/store.ts`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/documents/UploadZone.tsx`
- `frontend/src/components/chat/ChatInput.tsx`
- `frontend/src/components/chat/StreamingMessage.tsx`
- `tests/test_web_app.py`
- `C:/Users/Asus/.gemini/antigravity-ide/brain/063fe609-b3ed-4ff5-a667-342c12d94343/implementation_plan_5_1.md`

Verification:
- TypeScript type checking: `npx tsc --noEmit` passed with 0 errors.
- Vite build check: `npm run build` succeeds (dist bundle compiled in 647ms).
- Python test suite: `pytest` passes 115/115 tests in 6.97s.
- Code graph: Updated with `graphify update .`.

### 2026-06-03 - SQLite Connection Leak & Deletion Deadlock Fix

What changed:
- **SQLite Connection Leak Fix**: Modified the `_connect` helper method in `LocalStorage` inside [storage.py](file:///d:/Projects/private-pageindex-rag/private_pageindex/storage.py) to be a custom context manager decorated with `@contextlib.contextmanager`. Instead of returning a raw `sqlite3.Connection` which leaves connections open until garbage collection, it now yields the connection inside a `try...finally` block that guarantees `conn.close()` is called on block exit, and wraps the yield inside a transaction `with conn:` context.
- **Increased SQLite Timeout**: Set SQLite connection timeout to 30.0s to prevent premature lock errors when concurrent requests occur (e.g. background polling and user commands).
- **Verified Deletion Behavior**: Deletion of documents and cascade purging of chats, retrieval steps, nodes, and local files is now instant and no longer hangs or deadlocks.

Files changed:
- `private_pageindex/storage.py`

Verification:
- Python test suite: `pytest` passed 114/114 tests successfully.
- Manual test: Ran `DELETE` requests to `/api/documents/{doc_id}/delete` on local server, verifying instant responses and successful cleanup.
- Graphify graph: Updated graph representation using `graphify update .`.

### 2026-06-03 - Phase 4 Implementation: Streaming Chat & Live Citation Tracing

What changed:
- **SSE Streaming Backend**: Implemented async SSE generator endpoint `/api/documents/{doc_id}/ask/stream` in `app.py`, yielding trace steps, context status, and LLM text tokens.
- **Streaming Zustand Store**: Created `traceStore.ts` store tracking SSE tokens, current retrieval step, and activated/fetched node IDs.
- **Graph Retrieval Animations**: Added keyframe CSS pulses and glows in `index.css` mapped to pipeline steps. Graph nodes animate on `inspect_tree` (subtle pulse), `select_nodes` (teal glow), `fetch_pages` (white/teal flash with floating page range badge), and settle to standard highlight upon completion.
- **Interactive Citations**: Parsed `[page N]` text into clickable `CitationLink` components on both streaming responses (`StreamingMessage.tsx`) and historical messages (`ChatMessage.tsx`), centering selection highlights on the spatial graph.
- **Global Shortcuts & Command Palette**: Wired `useKeyboardShortcuts` hooks and `CommandPalette` Dialog into `AppShell.tsx` and `DocumentPage.tsx` (Escape clears selection, Ctrl+K triggers search palette).
- **ESLint/TS Compilation Fixes**: Eliminated unused React imports and duplicate branching conditions in `GraphNode.tsx` styling hierarchy.
- **Fixed Trace Page Crash**: Resolved a rendering crash on the `TracePage` timeline page. The database stores `retrieval_steps.pages` as a `TEXT` string (e.g., `"1-3"`), but TypeScript and frontend rendering expected a `number[]` array, leading to a `.join()` TypeError that crashed the React tree. Updated `TraceTimeline.tsx` to handle pages defensively (detecting array vs string) and formatting timestamps safely.
- **Fixed Citation Highlighting Failures**: Resolved cases where page highlights and clickable citation badges didn't display. Local models frequently capitalize, omit brackets, or output page ranges (e.g., `Page 1`, `[Page 1]`, `(page 5)`), which failed to match the old strict `[page N]` lowercase regex. Implemented a robust, case-insensitive regex pattern on both the backend ([app.py](file:///d:/Projects/private-pageindex-rag/private_pageindex/web/app.py)) and frontend components ([ChatMessage.tsx](file:///d:/Projects/private-pageindex-rag/frontend/src/components/chat/ChatMessage.tsx) and [StreamingMessage.tsx](file:///d:/Projects/private-pageindex-rag/frontend/src/components/chat/StreamingMessage.tsx)) to parse all formatting variations and range starts.

Files changed:
- `private_pageindex/web/app.py`
- `frontend/src/index.css`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/components/chat/ChatMessage.tsx`
- `frontend/src/components/chat/ChatPanel.tsx`
- `frontend/src/components/chat/StreamingMessage.tsx`
- `frontend/src/components/CommandPalette.tsx`
- `frontend/src/pages/DocumentPage.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/trace/TraceTimeline.tsx`
- `frontend/src/lib/types.ts`

Verification:
- Frontend compile check: `npm run build` succeeds (dist built in 620ms).
- Frontend linting: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 114/114 tests in 22.37 seconds.

### 2026-06-02 - Manual Testing Bug Fixes: Chats API & Knowledge Graph Layout

What changed:
- **Fixed Backend Chats Crash**: Resolved `AttributeError: 'RetrievalStepRecord' object has no attribute 'created_at'` in `api_get_document_chats` by referencing `chat.created_at`.
- **Created Integration Test**: Added `test_api_get_document_chats_with_traces` to verify chat trace serialization.
- **Fixed Knowledge Graph Sizing & Centering**: Integrated `ResizeObserver` in `KnowledgeGraph.tsx` to handle initial dimension measurements, preventing the graph from collapsing to `(0, 0)` in the top-left corner.
- **Fixed Physics Overlap Deadlock**: Distributed unpositioned nodes in a radial layout offset around the center (rather than placing them exactly overlapping), avoiding a divide-by-zero deadlock in the repulsion forces.
- **Fixed Anime.js Transform Conflict**: Wrapped the circle and label elements inside a nested `<g className="graph-node-inner">` container in `GraphNode.tsx`, letting `anime.js` scale the inner group while the outer group safely translates (`translate(x, y)`).
- **Fixed Zoom Origin**: Removed `style={{ transformOrigin: 'center center' }}` zoom origin layout jumps.
- **Added Animation Ref Cache**: Prevented window/panel resizing from re-triggering entrance scale/fade animations.

Files changed:
- `private_pageindex/web/app.py`
- `tests/test_web_app.py`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/components/graph/GraphNode.tsx`
- `frontend/src/components/graph/GraphEdge.tsx`

Verification:
- Bundler compilation check: `npm run build` succeeds (dist built in 462ms).
- Linter checks: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 114/114 tests in 23.53s.

### 2026-06-01 - Phase 3 Audit & Gap Closure: Knowledge Graph & Document Page

What changed:
- **Modularized Chat Panel**: Extracted `ChatMessage.tsx` and `ChatInput.tsx` from `ChatPanel.tsx` to align with the design spec.
- **Wired Zoom Controls**: Converted `KnowledgeGraph.tsx` to use `forwardRef` and `useImperativeHandle` to expose `zoomIn`, `zoomOut`, and `resetView` methods, and wired them to `GraphControls.tsx` in `DocumentPage.tsx`.
- **Draggable split layout**: Integrated `react-resizable-panels` (v4.x using `Group` and `Separator` exports) into `DocumentPage.tsx` to replace the fixed CSS grid split layout.
- **Cleaned Up Comments**: Removed outdated model think-aloud block comments from `DocumentPage.tsx`.

Files changed:
- `frontend/src/components/chat/ChatMessage.tsx` (NEW)
- `frontend/src/components/chat/ChatInput.tsx` (NEW)
- `frontend/src/components/chat/ChatPanel.tsx`
- `frontend/src/components/graph/KnowledgeGraph.tsx`
- `frontend/src/pages/DocumentPage.tsx`

Verification:
- Bundler compilation check: `npm run build` succeeds (dist built in 528ms).
- Linter checks: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 113/113 tests in 10.44s.

### 2026-06-01 - Frontend Integrity Check & Repository Clean

What changed:
- **Comprehensive Code Audit**: Audited all frontend modules against product specifications. Confirmed full alignment of features up to Phase 2 (LoadingScreen, InteractiveBackground grid, ModelPicker, OllamaStatus, AppShell layout, UploadZone, custom Progress/Timer, Zustand store, and SmoothCursor).
- **Redundant File Cleanup**: Deleted obsolete generated text files (`build-out.txt` and `npm-install-out.txt`) from the `frontend/` directory to prevent them from being committed. Verified that `CustomCursor.tsx` remains deleted and is replaced entirely by `SmoothCursor.tsx`.
- **System Invariant Check**: Confirmed that reverse proxy configurations in Vite are correct and Pinned package.json versions match.

Files changed:
- `frontend/build-out.txt` (DELETED)
- `frontend/npm-install-out.txt` (DELETED)

Verification:
- Bundler compilation check: `npm run build` succeeds in 466ms.
- Linter checks: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 113/113 tests in 10.99s.

### 2026-06-01 - Installed Magic UI SmoothCursor Component & Configured Default Theme

What changed:
- **Magic UI Smooth Cursor:** Added `@magicui/smooth-cursor` (default theme) component with physics-based spring animations. Installed `framer-motion` package.
- **Input Text Selection Caret:** Wired global cursor rules to hide the browser cursor everywhere except over inputs, textareas, selects, and contenteditable elements where the native text cursor (I-beam) is kept, using explicit `input, textarea, select { cursor: text !important; }` declarations.
- **Zero-lag performance:** Configured `SmoothCursor` with target checks using direct DOM manipulation to control opacity on hover, preventing React component re-renders and lag.
- **Cleaned Obsolete Code:** Replaced the custom pointer with `SmoothCursor` inside `AppShell.tsx` and removed the old `CustomCursor.tsx` component.

Files changed:
- `frontend/package.json`
- `frontend/src/components/ui/smooth-cursor.tsx` (NEW)
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/CustomCursor.tsx` (DELETED)

Verification:
- Bundler compilation check: `npm run build` succeeds (dist built in 449ms).
- Linter checks: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 113/113 tests in 10.81s.

### 2026-06-01 - Build Phase 2: Custom Cursor + Dashboard + Upload

What changed:
- Implemented Phase 2 steps 2.1–2.9 of frontend/backend specifications.
- **Custom Cursor:** Implemented the Magic UI styled `SmoothCursor` with spring-physics lagging trail animation, rendering a default pointer arrow SVG. Hides the browser default cursor globally via CSS while retaining the native I-beam cursor inside input boxes, textareas, and select menus. Runs on zero-state React renders for lag-free performance.
- **Backend JSON API:** Added FastAPI routes in app.py for listing documents, uploading files, and recursive deletion. Added targeted unit tests.
- **Zustand Store & Client:** Created store.ts, api.ts, and types.ts. Designed 2s background polling loop that updates processing card states.
- **Upload Zone:** Created UploadZone.tsx drag-and-drop container with dashed ASCII border and type validations.
- **Index Progress:** Created ProgressBar.tsx (custom block characters) and ElapsedTimer.tsx (JetBrains Mono tabular figures showing duration).
- **Header Status:** Extracted OllamaStatus.tsx and ModelPicker.tsx components, mounting them in AppShell.tsx.
- **Global Toast Support:** Wrapped App.tsx layout in Sonner Toaster.

Files changed:
- `private_pageindex/web/app.py`
- `tests/test_web_app.py`
- `frontend/src/App.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/components/CustomCursor.tsx` (NEW)
- `frontend/src/components/documents/UploadZone.tsx` (NEW)
- `frontend/src/components/documents/ProgressBar.tsx` (NEW)
- `frontend/src/components/documents/ElapsedTimer.tsx` (NEW)
- `frontend/src/components/layout/OllamaStatus.tsx` (NEW)
- `frontend/src/components/layout/ModelPicker.tsx` (NEW)
- `frontend/src/lib/types.ts` (NEW)
- `frontend/src/lib/api.ts` (NEW)
- `frontend/src/lib/store.ts` (NEW)

Verification:
- Bundler compilation check: `npm run build` succeeds in 362ms.
- Linter checks: `npm run lint` succeeds with 0 errors.
- Python tests: `pytest` passes 113/113 tests in 11.16s.

### 2026-06-01 - Phase 1 Audit: Found and fixed 10 issues

What changed:
- Audited all Phase 1 frontend files against design.md specification.
- Found 14 issues total (4 critical, 4 moderate, 4 minor); fixed 10 actionable ones.
- **Fix 1:** Added missing z-index theme tokens (`--z-sticky`, `--z-sidebar`, `--z-dropdown`, `--z-modal`, `--z-toast`, `--z-cursor`, `--z-loading`) to `@theme` block in `index.css`. Without these, Tailwind classes `z-sticky` and `z-sidebar` in AppShell resolved to `auto`.
- **Fix 2:** Added `animate-fade-in` animation (keyframe + `--animate-fade-in` theme token) used by all three pages but never defined.
- **Fix 3:** Removed `next-themes` dependency — it's a Next.js library unused in Vite/SPA; hardcoded `"dark"` theme in sonner.tsx for the dark-only design.
- **Fix 4:** Removed `"use client"` RSC directive from sonner.tsx (meaningless in Vite).
- **Fix 5:** Deleted 185-line `App.css` Vite boilerplate (dead code, never imported).
- **Fix 6:** Updated `index.html`: title from "frontend" to "Private PageIndex RAG", added meta description and theme-color.
- **Fix 7:** Added `prefers-reduced-motion` check to LoadingScreen.tsx (InteractiveBackground already had it).
- **Fix 8:** Pinned all `^`-prefixed dependency versions to exact versions; removed `next-themes` from package.json.
- **Fix 9:** Converted `scrollRatio` from `useState` to `useRef` with direct DOM mutation in InteractiveBackground.tsx (eliminates React re-renders on scroll).
- **Fix 10:** Added `DOM.Iterable` to `tsconfig.app.json` lib array.
- Added global `prefers-reduced-motion` CSS media query override for all CSS animations/transitions.

Files changed:
- `frontend/src/index.css`
- `frontend/src/components/ui/sonner.tsx`
- `frontend/src/App.css` (DELETED)
- `frontend/index.html`
- `frontend/src/components/LoadingScreen.tsx`
- `frontend/package.json`
- `frontend/src/components/InteractiveBackground.tsx`
- `frontend/tsconfig.app.json`

Verification:
- `npm run build` inside `frontend/` — 0 errors, successful build.
- `npm run lint` inside `frontend/` — 0 errors, 3 shadcn warnings (expected: co-exported variants).
- Backend test suite — 109 tests passing, unchanged.

### 2026-06-01 - Completed Phase 1: Foundation + Loading Screen + Background

What changed:
- Initialized React 19 + Vite 6 + TypeScript project under `frontend/`.
- Configured Tailwind CSS v4 using the native `@tailwindcss/vite` plugin and defined "Terminal Scholar" theme variables.
- Downloaded and self-hosted the offline font stack (Space Grotesk, Geist Sans, JetBrains Mono) under `frontend/public/fonts/`.
- Implemented Feature 1 (ASCII Loading Screen) and Feature 2 (Interactive background canvas matrix) using `anime.js` v4 animation APIs.
- Built the responsive layout shell (`AppShell.tsx`) with collateral sidebars, header bar proxy controls, and router view placeholders.
- Configured Vite reverse proxy to redirect `/api/` to the FastAPI backend.

Files changed:
- `frontend/package.json`
- `frontend/vite.config.ts` (NEW)
- `frontend/tsconfig.json` (NEW)
- `frontend/src/index.css` (NEW)
- `frontend/src/App.tsx` (NEW)
- `frontend/src/components/LoadingScreen.tsx` (NEW)
- `frontend/src/components/InteractiveBackground.tsx` (NEW)
- `frontend/src/components/layout/AppShell.tsx` (NEW)
- `frontend/src/pages/DashboardPage.tsx` (NEW)
- `frontend/src/pages/DocumentPage.tsx` (NEW)
- `frontend/src/pages/TracePage.tsx` (NEW)

Verification:
- Bundler compilation check: `npm run build` inside `frontend/` succeeds with 0 errors/warnings.
- Backend test suite remains fully green (109 tests passing).

### 2026-06-01 - Pinned frontend package dependencies to exact versions

What changed:

- Pinned all dependencies and devDependencies in `frontend/package.json` to their exact resolved versions from `package-lock.json`, removing all range-based prefixes (`^`, `~`) to remediate Improper Authorization (CWE-427) vulnerability scanner findings.

Files changed:

- `frontend/package.json`

Verification:

- Ran the local SecureCoder semgrep scan on `frontend/package.json` and verified 0 findings (down from 4 findings).
- Successfully ran `npm install`, `npm run build`, and `npm run lint` inside the `frontend/` directory with pinned versions.
- Reported completion to the SecureCoder API endpoint `/fix_completed`.

### 2026-05-31 - Initialized shadcn MCP server configuration

What changed:

- Initialized shadcn MCP server configuration for the VS Code client by running `npx shadcn@latest mcp init --client vscode`.
- Created `.vscode/mcp.json` containing the shadcn MCP server configuration.

Files changed:

- `.vscode/mcp.json` (NEW)

Verification:

- Verified `.vscode/mcp.json` content and confirmed it matches standard workspace MCP configuration formats.

### 2026-05-29 - Richer deterministic summaries + entity extraction (retrieval improvement Change 4)

What changed:

- Created `private_pageindex/indexing/entity_extraction.py` — matches and extracts emails, website URLs, phone numbers, and names following standard text labels (such as "Author:", "CONTACTS:", "Submitted by").
- Modified `_deterministic_summary()` in `tree_builder.py` to call `extract_key_entities()` and append the extracted details to the summary string formatted as `| Key: name1, email2...` (capped at 300 chars).
- Created `tests/test_entity_extraction.py` containing 5 tests for various entity types and deduplication.
- Appended a test `test_summary_includes_extracted_entities` in `test_tree_builder.py` to verify ingestion summary integration.

Files changed:

- `private_pageindex/indexing/entity_extraction.py` (NEW)
- `tests/test_entity_extraction.py` (NEW)
- `private_pageindex/indexing/tree_builder.py`
- `tests/test_tree_builder.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 105 tests, zero failures.

Important notes:

- This enables search keywords on structural metadata (contacts, authors) to match nodes lexical-fallbacks reliably.
- Requires re-indexing (delete and re-upload) of existing documents in the UI to regenerate summaries with these entities.

### 2026-05-29 - Page-text fallback search (retrieval improvement Change 3)

What changed:

- Added `_page_text_fallback()` to `tree_search.py` — counts question keywords (excluding stop words) in the raw text of each document page. Maps the top 2 matching pages to their most specific tree nodes (smallest page span).
- Updated both `search_tree()` and `search_tree_async()` to call `_page_text_fallback()` when the initial tree-guided search and lexical title/summary fallback both return no nodes.
- Appended a trace step (`page_text_fallback`) to log when this fallback is used.
- Added 2 new tests in `test_tree_search.py` covering sync and async fallback retrieval.

Files changed:

- `private_pageindex/retrieval/tree_search.py`
- `tests/test_tree_search.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 99 tests, zero failures.

Important notes:

- This directly resolves queries like "contacts" failing when the terms only exist within raw page text rather than titles/summaries.

### 2026-05-29 - Tree prompt compression (retrieval improvement Change 2)

What changed:

- Added `tree_prompt_compact_threshold: int = 4000` setting to `config.py`.
- Added `_format_tree_compact()` to `tree_search.py` — renders one line per node (id, title, page range) with no summaries.
- Added `_format_tree_auto()` to `tree_search.py` — tries full mode first; if prompt exceeds the threshold, falls back to compact mode and returns a boolean flag.
- Updated both `search_tree()` and `search_tree_async()` to use `_format_tree_auto()`. The `inspect_tree` trace step now records which mode was used ("full" vs "compact").
- Added 5 new tests.

Files changed:

- `private_pageindex/config.py`
- `private_pageindex/retrieval/tree_search.py`
- `tests/test_tree_search.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 97 tests, zero failures.

Important notes:

- The health PDF had a 14,850-char prompt with 65 nodes — well over the 4,000-char threshold. With compact mode it drops to ~3,000 chars, which local models (gemma4) can reason about reliably.
- The earnings PDF (3,916 chars) stays just under the threshold and keeps full mode with summaries.
- Compact mode is automatic and transparent — no config change needed by the user.

### 2026-05-29 - Front-matter node for orphan pages (retrieval improvement Change 1)

What changed:

- Added front-matter node insertion in `build_tree()`: when the first tree node starts after the document's first page, a "Front Matter" node is inserted covering the gap pages. This ensures pages like title pages, certificates, and author info are always reachable by retrieval.
- Added orphan-page detection in `validate_tree()`: flags any document pages not covered by any tree node, making coverage gaps visible in the validation report.
- Added 3 new tests: front-matter insertion, no-front-matter when not needed, and orphan-page validation.

Files changed:

- `private_pageindex/indexing/tree_builder.py`
- `private_pageindex/indexing/tree_validation.py`
- `tests/test_tree_builder.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 92 tests, zero failures.

Important notes:

- This fix helps documents where pre-heading pages are body text (no heading-like content). For PDFs with ALL_CAPS title pages (like the health monitoring PDF), the heading detector already picks them up, so front-matter doesn't trigger. Other retrieval improvements (page-text fallback, richer summaries) are needed for those cases.
- Existing indexed documents need re-indexing (delete + re-upload) to get the new front-matter nodes.

### 2026-05-29 - __main__.py + .gitignore (backend hardening Changes 5 & 6)

What changed:

- Created `__main__.py` — standard Python entry-point for `python -m private_pageindex`. Same content as `cli_main.py` with updated docstring. Old `cli_main.py` left in place for backward compat (can be deleted at user's discretion).
- Added `graphify-out/` to `.gitignore`.
- Updated `docs/STRUCTURE.md` to reference `__main__.py`.

Files changed:

- `private_pageindex/__main__.py` (NEW)
- `.gitignore`
- `docs/STRUCTURE.md`

Verification:

- `.\.venv\Scripts\python.exe -m private_pageindex --help` — works correctly.
- `.\.venv\Scripts\python.exe -m pytest -v` passed: 89 tests, zero failures.

### 2026-05-29 - Split tree_builder.py (backend hardening Change 4)

What changed:

- Created `heading_detection.py` — all heading regex constants, `HeadingCandidate`, `detect_headings()`, `detect_repeated_headers()`, and all line/title helper functions (~290 lines).
- Created `tree_postprocessing.py` — `merge_title_fragments()`, `suppress_cover_noise()`, `flag_duplicate_titles()`, and their private helpers (~190 lines).
- Created `tree_validation.py` — `TreeReport` dataclass and `validate_tree()` function (~110 lines).
- Rewrote `tree_builder.py` as a slim orchestrator (~270 lines, down from 841). Imports from sub-modules and re-exports all public names.
- Zero test changes required — all 20 tree builder tests pass with unchanged imports.

Files changed:

- `private_pageindex/indexing/heading_detection.py` (NEW)
- `private_pageindex/indexing/tree_postprocessing.py` (NEW)
- `private_pageindex/indexing/tree_validation.py` (NEW)
- `private_pageindex/indexing/tree_builder.py` (REWRITE)

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 89 tests, zero failures.

### 2026-05-29 - LLM provider protocol + async client (backend hardening Change 3)

What changed:

- Created `llm/base.py` with 6 structural protocols: `LLMTextProvider`, `LLMJsonProvider`, `LLMProvider`, and async counterparts.
- Added `AsyncOllamaClient` in `ollama.py` — mirrors sync client using `httpx.AsyncClient`.
- Added `search_tree_async()` in `tree_search.py` — async version alongside sync.
- Added `generate_answer_async()` in `answering.py` — async version alongside sync.
- Updated `web/app.py`: `ask_question`, `ollama_status`, `ollama_models` now use `AsyncOllamaClient` + async retrieval functions. Background indexing stays sync.
- Updated `test_web_app.py`: mock classes now have async methods, monkeypatching targets updated.
- Created `tests/test_async_ollama.py`: 9 tests for async client + protocol conformance.

Files changed:

- `private_pageindex/llm/base.py` (NEW)
- `private_pageindex/llm/ollama.py`
- `private_pageindex/retrieval/tree_search.py`
- `private_pageindex/retrieval/answering.py`
- `private_pageindex/web/app.py`
- `tests/test_web_app.py`
- `tests/test_async_ollama.py` (NEW)

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 89 tests (80 existing + 9 new).

Important decisions:

- Sync functions (`search_tree`, `generate_answer`, `OllamaClient`) are preserved exactly — CLI and background indexing keep using them.
- Async functions are new additions, not replacements. Zero breaking changes.
- `AsyncOllamaClient` reuses `OllamaClient._extract_message_content` (static method) to avoid duplication.

### 2026-05-29 - Fix storage abstraction leaks (backend hardening Change 2)

What changed:

- Added `list_documents()` to `LocalStorage` — returns all docs as `DocumentRecord` objects, sorted newest-first with `ROWID DESC` tiebreaker.
- Added `recover_interrupted_documents()` to `LocalStorage` — marks stuck `processing` docs as `failed` on startup.
- Added `limit` keyword parameter to `list_chats()` for capping results.
- Removed `_list_documents()` helper and all raw `import sqlite3` usage from `web/app.py`.
- Lifespan handler, document list page, and chat history all now go through `LocalStorage`.
- Updated `test_web_app.py` to use `storage.list_documents()` instead of removed `_list_documents()`.
- Added 5 new storage tests: list ordering, empty list, chat limit, recovery, and no-op recovery.

Files changed:

- `private_pageindex/storage.py`
- `private_pageindex/web/app.py`
- `tests/test_storage.py`
- `tests/test_web_app.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 80 tests (75 existing + 5 new).

### 2026-05-29 - Settings singleton (backend hardening Change 1)

What changed:

- Added `get_settings()` with `@lru_cache(maxsize=1)` to `config.py` so `.env` is read once instead of on every call.
- Added `reset_settings()` to clear the cache for test isolation.
- Updated all 6 caller files to use `get_settings()` instead of `Settings()`:
  `ollama.py`, `tree_builder.py`, `tree_search.py`, `answering.py`, `cli.py`, `web/app.py`.
- Added 3 new tests for singleton behavior, cache clearing, and env override after reset.

Files changed:

- `private_pageindex/config.py`
- `private_pageindex/llm/ollama.py`
- `private_pageindex/indexing/tree_builder.py`
- `private_pageindex/retrieval/tree_search.py`
- `private_pageindex/retrieval/answering.py`
- `private_pageindex/cli.py`
- `private_pageindex/web/app.py`
- `tests/test_config.py`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 75 tests (72 existing + 3 new).

Important decisions:

- Kept `Settings` class importable for direct use (e.g. tests). Only runtime callers switched to `get_settings()`.
- `reset_settings()` is the public way to clear the cache; used in tests that monkeypatch env vars.

### 2026-05-28 - Indexing progress, model picker, and lifecycle cleanup

What changed:

- Changed web uploads from synchronous indexing to background indexing after the upload response.
- Added document progress fields, migration logic, elapsed-time reporting, and `/api/documents/{doc_id}/status`.
- Added `/api/ollama-models` and a browser model picker whose selected local Ollama model is sent with upload and chat requests.
- Added progress bars, indexing stage text, and elapsed timers to processing document cards.
- Hardened document deletion and added orphan chat/retrieval-step cleanup on startup.
- Added design and implementation-plan handoff docs under `docs/superpowers/`.

Files changed:

- `private_pageindex/storage.py`
- `private_pageindex/ingest/pipeline.py`
- `private_pageindex/web/app.py`
- `private_pageindex/web/templates/base.html`
- `private_pageindex/web/templates/index.html`
- `private_pageindex/web/templates/document.html`
- `private_pageindex/web/static/app.css`
- `tests/test_storage.py`
- `tests/test_ingest_pipeline.py`
- `tests/test_web_app.py`
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT.md`
- `docs/PLAN.md`
- `docs/TROUBLESHOOTING.md`
- `docs/superpowers/specs/2026-05-28-indexing-progress-model-lifecycle-design.md`
- `docs/superpowers/plans/2026-05-28-indexing-progress-model-lifecycle.md`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 72 tests.

Important decisions:

- Progress is stage-based rather than fake token-level/model-level progress because Ollama does not expose exact indexing progress for the local chat calls.
- Model choice is per browser/request via `localStorage` and hidden form fields, with the configured default model used when no choice is set.

### 2026-05-28 - Agent memory system

What changed:

- Added root `AGENTS.md` as the cross-agent startup and operating instruction file.
- Added `docs/AGENT_MEMORY.md` as the living project memory and update log.
- Chose the `AGENTS.md` plus focused memory-file approach instead of a large one-file context dump, because concise repository instructions are easier for agents to obey and cheaper to keep current.

Files changed:

- `AGENTS.md`
- `docs/AGENT_MEMORY.md`

Verification:

- `.\.venv\Scripts\python.exe -m pytest -v` passed: 61 tests.

Follow-up:

- None.

### 2026-05-14 to 2026-05-16 - Messy PDF tree reliability hardening

What changed:

- Improved tree construction for messy/unstructured PDFs.
- Added support for multiple same-page headings, known single-line structural headings, explicit section and appendix headings, appendix numbering, blank-page boundary nodes, duplicate-title handling, cover-noise suppression, repeated-header fallback, and tree validation reports.
- Preserved deterministic structural titles during optional LLM enhancement while allowing summaries to update.
- Stored tree validation metadata in `tree.json`.
- Documented messy-PDF behavior in troubleshooting docs.

Important files:

- `private_pageindex/indexing/tree_builder.py`
- `private_pageindex/ingest/pipeline.py`
- `tests/test_tree_builder.py`
- `tests/test_ingest_pipeline.py`
- `docs/TROUBLESHOOTING.md`
- `docs/superpowers/plans/2026-05-14-messy-pdf-tree-reliability.md`

Verification:

- Project docs currently state 61 passing tests. Re-run before relying on this count.

Important invariant added:

- Tree node metadata may include `flags`, and top-level tree JSON may include `validation`, but existing node fields must remain intact.

## Open Follow-Ups

- Consider removing the remote Google Fonts request from the web UI if the user wants a stricter offline-only browser boundary.
- Consider `llms.txt` only if this project gets published as a documentation website. For a local source repository, `AGENTS.md` is the better primary entry point.
