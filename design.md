# Design System: Private PageIndex RAG

> **For agentic workers:** This document is the single source of truth for all frontend implementation. Read it fully before writing any UI code. Every design decision references skills loaded from `.agents/` and the project's backend contracts.

**Project:** `private-pageindex-rag` — fully private, local-first document RAG  
**Stack:** React 19 + Vite 6 + TypeScript + Tailwind CSS 4 + shadcn/ui  
**Animation Engine:** anime.js  
**Font Hosting:** Self-hosted (fully offline)  
**Backend:** FastAPI (unchanged)

---

## 1. Visual Theme & Atmosphere

**Atmosphere Rating** (per `stitch-design-taste` skill):

- **Density:** 6/10 — "Daily App Balanced" with occasional "Cockpit Dense" data displays
- **Variance:** 7/10 — Asymmetric layouts, non-standard grid breaks, ASCII decorative elements
- **Motion:** 7/10 — "Fluid CSS" with anime.js-powered perpetual micro-interactions and spring physics

**Scene sentence** (per `impeccable` skill): *A solo developer running a local RAG system late at night on a 27-inch monitor in a dim room, watching ASCII-art loading screens while their local LLM processes a 200-page PDF. The interface is their private command center — no cloud, no tracking, just them and their documents.*

This forces: **dark theme, monospace-heavy, terminal-native aesthetic with warm undertones to avoid clinical coldness.**

**Design Identity — "Terminal Scholar":**

The UI fuses the raw tactile energy of a terminal emulator with the structured clarity of an academic research tool. It feels like a private document laboratory — alive with subtle ASCII textures and reactive backgrounds that respond to the user's presence. Every long-running operation is visible and time-tracked. The knowledge graph replaces flat trees with a spatial, interactive map of document structure. Citation tracing unfolds live, in sync with the LLM's reasoning.

The aesthetic is deliberately **not** generic dark-mode SaaS. It is not neon-on-black cyberpunk. It is not soft pastel productivity. It is Terminal Scholar: precise, textured, private, alive.

---

## 2. Color Palette & Roles

Per `stitch-design-taste`: maximum 1 accent color, saturation below 80%, no pure black, no neon/outer glow shadows, no "AI Purple/Blue Neon."

Per `impeccable`: OKLCH-aware, tint every neutral toward the brand hue.

### System Colors

| Token | Name | Hex | OKLCH | Role |
|---|---|---|---|---|
| `--bg-void` | Charcoal Void | `#0C0C0E` | `oklch(0.10 0.005 280)` | App background, deepest layer |
| `--bg-surface` | Slate Surface | `#141417` | `oklch(0.14 0.005 280)` | Card/panel backgrounds |
| `--bg-elevated` | Steel Elevated | `#1C1C21` | `oklch(0.18 0.006 280)` | Modals, dropdowns, hover states |
| `--bg-interactive` | Iron Interactive | `#242429` | `oklch(0.21 0.006 280)` | Active/selected items |
| `--border-dim` | Graphite Hairline | `#2A2A30` | `oklch(0.24 0.005 280)` | Subtle dividers, card borders |
| `--border-default` | Pewter Line | `#3A3A42` | `oklch(0.30 0.006 280)` | Standard borders, tree branches |
| `--border-bright` | Silver Edge | `#4A4A55` | `oklch(0.38 0.007 280)` | Focused borders, hover states |
| `--text-primary` | Bone White | `#E4E4E8` | `oklch(0.92 0.005 280)` | Primary body text, headings |
| `--text-secondary` | Ash Gray | `#8A8A96` | `oklch(0.62 0.010 280)` | Secondary text, metadata, timestamps |
| `--text-tertiary` | Smoke Gray | `#5A5A66` | `oklch(0.43 0.010 280)` | Hints, placeholders, disabled |
| `--text-inverse` | Charcoal Ink | `#0C0C0E` | `oklch(0.10 0.005 280)` | Text on accent backgrounds |

### Accent Color — Mineral Teal

| Token | Name | Hex | OKLCH | Role |
|---|---|---|---|---|
| `--accent` | Mineral Teal | `#2DD4A8` | `oklch(0.78 0.14 170)` | Primary CTA, focus rings, active nodes |
| `--accent-dim` | Deep Teal | `#1FAF8A` | `oklch(0.68 0.12 170)` | Hover state for accent |
| `--accent-ghost` | Teal Ghost | `rgba(45,212,168,0.08)` | — | Subtle accent tint on surfaces |
| `--accent-glow` | Teal Glow | `rgba(45,212,168,0.20)` | — | Node activation glow in knowledge graph |

### Semantic Colors

| Token | Name | Hex | Role |
|---|---|---|---|
| `--color-info` | Signal Cyan | `#22D3EE` | Ollama status connected, info states |
| `--color-warning` | Warm Amber | `#F59E0B` | Processing, indexing in progress |
| `--color-error` | Coral Red | `#EF4444` | Errors, delete, failed states |
| `--color-success` | Mineral Teal | `#2DD4A8` | Completed, connected, confirmed |

### Banned Colors (per `stitch-design-taste`)
- Pure black `#000000` — always use `--bg-void` or darker neutrals
- Purple/violet accents — no `#7C3AED`, `#8B5CF6`, or similar
- Neon green `#00FF00` — too cyberpunk; use Mineral Teal instead
- Blue neon glow — no outer glow shadows in blue spectrum

---

## 3. Typography Rules

Per `frontend-design` skill: **NEVER use generic fonts (Inter, Roboto, Arial, system fonts).**  
Per `stitch-design-taste` skill: **Inter is BANNED for premium/creative contexts.**  
Per `ui-ux-pro-max` skill: **Use tabular/monospaced figures for data columns, prices, and timers.**

### Font Stack

| Role | Font | Weight | Usage |
|---|---|---|---|
| **Display / Headlines** | **Space Grotesk** | 500–700 | Page titles, hero text, section headers. Geometric, distinctive, not overused in RAG tools. Track-tight. |
| **Body** | **Geist Sans** | 400–500 | Paragraph text, descriptions, chat answers. Clean, modern, engineered for screens. Relaxed leading. |
| **Mono / Data** | **JetBrains Mono** | 400–500 | Node IDs, page numbers, timers, code, progress stages, ASCII art, tree branches. Tabular figures. |

> **Note:** Per `stitch-design-taste`, Space Grotesk is flagged as a common convergence risk. However, for a terminal-scholar aesthetic paired with JetBrains Mono, it provides the right geometric tension. If this feels generic during implementation, substitute **Outfit** or **Cabinet Grotesk**.

### Type Scale

```
--text-xs:     0.75rem / 12px     line-height: 1.5   // Timestamps, hints, node IDs
--text-sm:     0.8125rem / 13px   line-height: 1.5   // Metadata, tree summaries, badges
--text-base:   0.9375rem / 15px   line-height: 1.6   // Body text, chat messages
--text-lg:     1.125rem / 18px    line-height: 1.4   // Section headers, card titles
--text-xl:     1.5rem / 24px      line-height: 1.3   // Page titles
--text-2xl:    2rem / 32px        line-height: 1.2   // Hero/loading text
--text-3xl:    2.75rem / 44px     line-height: 1.1   // ASCII art display
```

### Typography Rules
- Body text line length capped at 65–75ch (per `ui-ux-pro-max` §6, `impeccable`)
- Hierarchy through scale + weight contrast ≥1.25 ratio between steps (per `impeccable`)
- All timer/progress/numeric values use JetBrains Mono for tabular alignment
- ASCII decorative elements exclusively use JetBrains Mono
- All fonts self-hosted as `.woff2` in `frontend/public/fonts/` — zero external requests

---

## 4. Component Hierarchy & Stylings

Per `shadcn` skill: use semantic colors (`bg-primary`, `text-muted-foreground`), never raw hex in components. Per `stitch-design-taste`: no custom mouse cursors as decoration. The browser default cursor is used throughout.

### Button System

| Variant | Style | Active State |
|---|---|---|
| **Primary** | `--accent` fill, `--text-inverse` text, sharp corners (0px radius) | `-1px translateY` + slight darken (per `stitch-design-taste`) |
| **Secondary** | `--border-default` border, transparent fill, `--text-primary` text | `--bg-interactive` fill on hover |
| **Ghost** | No border, no fill, `--text-secondary` text | `--accent-ghost` background on hover |
| **Destructive** | `--color-error` fill, `--text-primary` text | `-1px translateY` + darken |

### Card System

Per `stitch-design-taste`: "Use cards ONLY when elevation communicates hierarchy."  
Per `impeccable`: "Cards are the lazy answer. Use them only when they're truly the best affordance."

- Document cards on the dashboard: `--bg-surface` fill, `--border-dim` 1px border, **sharp corners** (0px radius)
- Chat messages: no card — use alternating background tints + left-align without wrapping border
- Tree nodes: inline list items with `--border-dim` left-border for indentation hierarchy
- Trace steps: vertical timeline with connector lines, not enclosed cards

### Input System

Per `ui-ux-pro-max` §8: visible label per input, error below field, focus ring in accent color.

- Label above input, always visible (never placeholder-only)
- `--bg-surface` background, `--border-default` border
- Focus: `--accent` border + `0 0 0 2px var(--accent-ghost)` ring
- Error: `--color-error` border + error text below in `--color-error`
- Chat input: full-width, monospaced placeholder text ("Ask a question..."), JetBrains Mono

### Loading States

Per `stitch-design-taste`: "Skeletal loaders matching layout dimensions — no generic circular spinners."  
Per `ui-ux-pro-max` §3: "Use skeleton screens / shimmer instead of long blocking spinners for >1s operations."

- Skeleton shimmer on document cards during load
- ASCII loading screen for initial app boot (Feature 1)
- Progress bars with block characters for indexing (Feature 4)

### ASCII Intensity: Medium

Per user specification: "medium — not overly dense, not too sparse."

ASCII elements are used for:
- Loading screen animation (primary)
- Section dividers: `──────` or `════════`
- Tree branch connectors: `├── `, `└── `, `│   `
- Progress bars: `[■■■■░░░░░░]`
- Status indicators: `●` connected, `○` disconnected
- Thinking/processing: `▒░▓ Processing ▓░▒`

ASCII is **not** used for:
- Card borders (use CSS borders instead)
- Button text styling (buttons use standard text)
- Input field decorations
- Navigation elements

---

## 5. Layout Principles

Per `ui-ux-pro-max` §5: mobile-first, 375/768/1024/1440 breakpoints, no horizontal scroll.  
Per `stitch-design-taste`: CSS Grid over Flexbox math, max-width containment (1400px).  
Per `impeccable`: vary spacing for rhythm, same padding everywhere is monotony.

### Primary Layout: App Shell

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER (sticky, 56px)                                     │
├────────────┬────────────────────────────────────────────────┤
│  SIDEBAR   │  MAIN CONTENT                                 │
│  (260px     │  (flex-1, max-w: 1140px)                     │
│  collaps    │                                               │
│  to 0px)    │                                               │
│            │                                               │
├────────────┴────────────────────────────────────────────────┤
│  FOOTER (40px)                                             │
└─────────────────────────────────────────────────────────────┘
```

### Spacing System (4px base, per `ui-ux-pro-max` §5)

```
--space-1:  4px        // Tight inline spacing
--space-2:  8px        // Icon padding, badge margins
--space-3:  12px       // Input padding, small gaps
--space-4:  16px       // Card padding, standard gaps
--space-6:  24px       // Section internal padding
--space-8:  32px       // Section gaps
--space-12: 48px       // Major section separations
--space-16: 64px       // Hero vertical padding
```

### Border Radius

**0px everywhere** (the "Terminal Scholar" signature). Exception:
- Avatar/profile images: 4px (subtle rounding to distinguish from rectangular cards)
- Toast notifications: 2px (minimal differentiation from page content)

### Z-Index Scale (per `ui-ux-pro-max` §5)

```
--z-base:      0       // Standard content
--z-sticky:    10      // Sticky header
--z-sidebar:   20      // Sidebar overlay on mobile
--z-dropdown:  30      // Dropdowns, popovers
--z-modal:     40      // Modals, command palette
--z-toast:     50      // Toast notifications
--z-loading:   1000    // Full-screen loading overlay
```

---

## 6. Motion & Interaction Philosophy

Per user specification: **Use anime.js for all animations.**  
Per `ui-ux-pro-max` §7: duration 150–300ms for micro-interactions, use transform/opacity only, respect `prefers-reduced-motion`.  
Per `stitch-design-taste`: spring physics default, perpetual micro-interactions, staggered orchestration.  
Per `impeccable`: ease out with exponential curves, no bounce/elastic.

### anime.js Configuration

```javascript
// Default easing for UI transitions
const UI_EASE = 'easeOutExpo';

// Spring-like easing for interactive elements
const SPRING_EASE = 'spring(1, 80, 10, 0)';

// Duration tokens
const DURATION = {
  instant: 100,     // Hover state changes
  fast: 200,        // Button press, toggle
  normal: 300,      // Panel open/close, page transition
  slow: 500,        // Modal entrance, loading screen
  crawl: 1000,      // Knowledge graph layout animation
};
```

### Animation Principles

1. **Enter vs Exit:** Exit animations are 60–70% of enter duration (per `ui-ux-pro-max` §7)
2. **Staggered reveals:** List/grid items stagger by 40ms per item (per `stitch-design-taste`)
3. **Hardware accelerated only:** animate `transform` and `opacity` exclusively — never `width`, `height`, `top`, `left` (per `stitch-design-taste`, `impeccable`)
4. **Interruptible:** All animations must be interruptible by user input (per `ui-ux-pro-max` §7)
5. **Reduced motion:** Wrap all anime.js calls in a `prefers-reduced-motion` check; reduce to instant opacity transitions when enabled

### Feature-Specific Motion

| Feature | Animation | Engine | Duration |
|---|---|---|---|
| Loading screen ASCII | Character-by-character reveal + dot-loader fallback | anime.js timeline | 2–3s total |
| Interactive background | Continuous particle/ASCII grid animation responding to mouse position | anime.js + requestAnimationFrame | Perpetual |
| Progress bar | Incremental fill with easeOutExpo, timer count with tabular number flipping | anime.js + setInterval | Real-time (1s timer, smooth bar fill) |
| Knowledge graph | Force-directed layout settling, node highlight pulse on selection | anime.js + d3-force | 800ms layout settle, 300ms pulse |
| Live citation trace | Node glow activation synced to SSE token stream, pulse + ring expand | anime.js | 400ms per node activation |

---

## 7. Feature Specifications

### Feature 1: ASCII Loading Screen

**Trigger:** Initial app load (before React hydration completes) and route transitions with data loading.

**Primary:** ASCII GIF assets provided by the user, rendered as the loading indicator. These are actual GIF image files displaying ASCII-art animation.

**Fallback:** If GIF assets fail to load (network error, missing file), fall back to a custom dot-loader:
```
Loading ·
Loading · ·
Loading · · ·
Loading · ·
Loading ·
```
Animated with anime.js opacity stagger, using JetBrains Mono.

**Layout:**
```
┌──────────────────────────────────┐
│                                  │
│        [ASCII GIF or             │
│         dot-loader]              │
│                                  │
│     PRIVATE PAGEINDEX RAG        │  ← Space Grotesk, --text-lg
│     Loading documents...         │  ← Geist Sans, --text-sm, --text-secondary
│                                  │
└──────────────────────────────────┘
```

**Implementation:**
- Pre-React: a lightweight HTML/CSS loading screen in `index.html` (no framework dependency)
- Post-React: a `<LoadingScreen />` component for route transitions
- anime.js fades the loader out with `easeOutExpo` over 500ms once content is ready

---

### Feature 2: Interactive Background

**Effect:** Subtle reactive background that responds to mouse position, scroll depth, and idle state.

**Approach:** ASCII grid / dot matrix rendered on a `<canvas>` element, full-viewport behind all content.

**Behavior:**
- **Mouse interaction:** Characters nearest to the cursor brighten or shift (radius ~120px). Characters use JetBrains Mono glyph set: `. · + * # @ %`
- **Scroll depth:** Background color subtly shifts from `--bg-void` to a slightly warmer tone as user scrolls deeper into content
- **Idle state:** After 5 seconds of no mouse movement, a slow wave animation ripples across the grid (anime.js timeline, 3s cycle)
- **Performance:** Canvas renders at 30fps max, characters are pre-computed grid cells (not individual DOM elements). Per `vercel-react-best-practices` `rendering-content-visibility`: canvas is `content-visibility: auto` when not in viewport

**Constraints:**
- Opacity never exceeds 0.06 — barely visible, felt more than seen
- Must not interfere with text readability (per `ui-ux-pro-max` §1 contrast rules)
- `prefers-reduced-motion`: disable all animation, show static faint grid

---

### ~~Feature 3: Custom Interactive Cursor~~ — **REMOVED**

> **Status: Removed (2026-06-05).** The `SmoothCursor` component and `CursorToggle` toggle switch have been deleted from the project. The browser default cursor is used. Do not reinstate this feature unless the user explicitly requests it.

---

### Feature 4: Live Progress Bar with Elapsed Time

**Existing backend contract:** `/api/documents/{doc_id}/status` returns:
```json
{
  "progress_percent": 45,
  "progress_stage": "building tree",
  "elapsed_seconds": 87
}
```

**Display:**

```
┌────────────────────────────────────────────────────────┐
│  report.pdf                                            │
│  ──────────────────────────────────────────────────── │
│  [█████████-----------]  45%  · building tree  01:27  │
└────────────────────────────────────────────────────────┘
```

**Components:**
- `<ProgressBar percent={45} />` — fills smoothly with anime.js `easeOutExpo` (never jumps)
- `<ElapsedTimer startedAt={isoString} />` — counts up in real-time, formatted as `mm:ss`, JetBrains Mono tabular figures
- `<StageLabel stage="building tree" />` — monospace text, fades between stages with crossfade (per `ui-ux-pro-max` §7)

**Behavior:**
- Polls `/api/documents/{doc_id}/status` every 1 second while document status is `processing`
- Progress bar width animates smoothly between poll values (never snaps)
- Timer counts locally between polls (JavaScript `setInterval`), syncs to backend `elapsed_seconds` on each poll
- On completion: progress bar fills to 100%, stage changes to "completed", bar turns `--color-success`
- On failure: bar turns `--color-error`, stage shows error message

---

### Feature 5: Interactive Knowledge Graph

**Replaces:** The current flat tree viewer in `document.html`.

**Data source:** `tree.json` structure:
```json
{
  "nodes": [
    {
      "node_id": "0001",
      "title": "Introduction",
      "start_page": 1,
      "end_page": 3,
      "summary": "Overview of the document...",
      "nodes": [
        { "node_id": "0001.01", "title": "Background", ... }
      ]
    }
  ]
}
```

**Visualization:** Math-based settled force-directed or circular layout using `d3-force` + custom bounding calculations.

**Node rendering:**
- Nodes are circles with dynamic sizing based on depth (root nodes are larger: 10px-16px radius, children are smaller).
- Labels are rendered as monospace elements positioned with absolute vertical offsets under/over the node circle to prevent overlap.
- Node fill: `--bg-surface` default, `--accent-ghost` when hovered, `--accent` when selected.
- Active nodes during SSE RAG query stream pulse visually with `--accent-glow`.

**Edge rendering:**
- Relationships shown as lines connecting parent and child nodes.
- Edge base color: dynamic `--accent` (Mineral Teal).
- Dynamic path tracing: edges highlight and thicken (`isActivated`, `isFetched`, `isSelected`) to visually trace RAG operations.

**Interactions:**
| Action | Behavior |
|---|---|
| **Click node** | Select node, show details panel (title, summary, page range). Highlight in accent. |
| **Double-click** | Expand/collapse children. |
| **Hover node** | Highlight node + connected edges, show tooltip with node details/summary. |
| **Zoom / Pan** | Disabled (static layout centering guarantees graph visibility within viewport). |
| **Click node + "Ask about this"** | Pre-fill chat input with context about the selected node. |

**Layout algorithm:**
- Centered layout: Computes the graph bounding box exactly once and centers/scales it mathematically using a dynamic transform to fit the panel bounds.
- Node collision radius: Dynamically determined based on label character length (`node.radius + title.length * 3.5 + 16`) to space nodes horizontally, eliminating overlaps.
- Mathematical circular layout: Spaces nodes evenly along a circle circumference scaled by the number of nodes to ensure perfect label readability.

---

### Feature 6: Live Citation Tracing During LLM Response

**Existing flow** (from [tree_search.py](file:///d:/Projects/private-pageindex-rag/private_pageindex/retrieval/tree_search.py)):
1. `inspect_tree` — format tree for LLM
2. `select_nodes` — LLM selects relevant node_ids
3. `fetch_pages` — retrieve pages for selected nodes
4. `generate_answer` — LLM generates grounded answer

**New flow for live tracing:**

The backend must expose an SSE streaming endpoint that emits trace events in real-time as the retrieval pipeline executes:

```
POST /api/documents/{doc_id}/ask/stream

SSE events:
  data: {"type": "trace", "step": "inspect_tree", "detail": "Formatted 8 nodes (2,341 chars)"}
  data: {"type": "trace", "step": "select_nodes", "node_ids": ["0001", "0003.02"], "reason": "..."}
  data: {"type": "trace", "step": "fetch_pages", "node_id": "0001", "pages": "1-3"}
  data: {"type": "trace", "step": "fetch_pages", "node_id": "0003.02", "pages": "12-14"}
  data: {"type": "token", "text": "The"}
  data: {"type": "token", "text": " document"}
  data: {"type": "token", "text": " states"}
  ...
  data: {"type": "done", "chat_id": "abc-123", "answer": "full text...", "citations": ["page 1", "page 12"]}
```

**Visual behavior in knowledge graph:**

| SSE Event | Graph Animation |
|---|---|
| `inspect_tree` | All nodes briefly pulse with `--text-tertiary` outline (scan effect), 400ms |
| `select_nodes` | Selected nodes activate: `--accent-glow` ring expands outward (anime.js, 600ms), node fill transitions to `--accent-ghost` |
| `fetch_pages` | Per-node: node glows brighter momentarily, page range badge appears below node |
| `token` | Tokens stream into chat panel. No graph effect. |
| `done` | Activated nodes settle into persistent highlight. Trace summary appears in sidebar. |

**Implementation:**
- Frontend uses `@microsoft/fetch-event-source` for POST-capable SSE
- Knowledge graph component subscribes to trace events via a shared Zustand store
- Each trace event triggers an anime.js animation on the corresponding graph node(s)
- Animations are queued/sequenced via anime.js timeline to prevent overlapping

---

## 8. shadcn/ui Component Manifest (MCP-Verified)

All components below were confirmed available via the `shadcn` MCP server `search_items_in_registries` queries:

### Core UI Components Used

| Component | Registry | Purpose in This Project |
|---|---|---|
| `sidebar` | `@shadcn/ui` | App shell sidebar with document list and collapsible chat session histories. |
| `command` | `@shadcn/ui` | Command palette dialog layout (triggered by `Ctrl+K`). |
| `progress` | `@shadcn/ui` | Custom progress bar layout with block overrides. |
| `skeleton` | `@shadcn/ui` | Shimmer loading placeholders for document cards and streaming RAG responses. |
| `sonner` | `@shadcn/ui` | Action toasts (upload success, deletion success, errors). |
| `alert-dialog` | `@shadcn/ui` | Cascade deletion confirmation modal. |
| `scroll-area` | `@shadcn/ui` | Custom scrollbar panels for document graphs, histories, and chats. |
| `resizable` | `@shadcn/ui` | Split pane dragging handlers separating graph and chat panels. |
| `tooltip` | `@shadcn/ui` | Dynamic node metadata detail tooltip on node hover. |
| `separator` | `@shadcn/ui` | Custom horizontal and vertical dividers. |
| `badge` | `@shadcn/ui` | Document status tags and page range indicators. |
| `collapsible` | `@shadcn/ui` | Tree category expansion nodes in the sidebar. |
| `button` | `@shadcn/ui` | Accent CTAs, secondary action triggers, and destructors. |
| `input` | `@shadcn/ui` | Monospaced chat inputs and file ingestion drag-zones. |
| `dialog` | `@shadcn/ui` | Basic modal containers. |
| `dropdown-menu` | `@shadcn/ui` | Ollama model selection dropdown list. |

### Custom Component Wrappers

| Component | Wraps | Custom Style/Behavior |
|---|---|---|
| `AsciiProgress` | `progress` | Custom block characters (`█` and `-`) for smooth indexing progress representation. |
| `AsciiSeparator` | `separator` | Custom text character dividers (`═══`, `───`) to match the monospace style. |
| `LoadingScreen` | — | ASCII GIF loading screen with a standard dot-loader fallback. |
| `InteractiveBackground` | — | Dynamic canvas overlay tracking mouse motion and rendering a reactive ASCII dot-matrix. |
| `KnowledgeGraph` | — | Settled D3 force-directed circular mapping engine with static centering transforms. |
| `StreamingMessage` | — | Token-by-token stream visual rendering. |
| `ThinkingIndicator` | — | Custom monospaced processing indicator (`▒░▓ Processing ▓░▒`). |
| `ElapsedTimer` | — | Tabular, real-time mm:ss ticking timer using JetBrains Mono. |
| `CitationLink` | — | Custom parsed links mapping clicked references (`[page N]`) back to highlighted graph nodes. |

### Third-Party Frontend Dependencies

| Package | Purpose | Size Impact |
|---|---|---|
| `animejs` | Staggered reveals, progress bar transitions, token streams, and RAG node pulses. | ~17KB |
| `d3-force` + `d3-hierarchy` | Math layouts and node spacing coefficients in the knowledge graph. | ~30KB (d3 subset) |
| `@microsoft/fetch-event-source` | Server-Sent Events (SSE) listener for question responses. | ~5KB |
| `zustand` | State management (document polling, active sessions, and streams). | ~3KB |
| `lucide-react` | SVG vector icons. | Tree-shakeable |
| `react-router-dom` | SPA client routing. | ~14KB |

---

## 9. Anti-Patterns (Banned)

Per `stitch-design-taste`, `impeccable`, `frontend-design` skills:

### Visual Bans
- ❌ Emojis as icons — use Lucide React SVGs exclusively.
- ❌ Inter font — use Space Grotesk + Geist Sans + JetBrains Mono.
- ❌ Pure black `#000000` — use `--bg-void` (`#0C0C0E`).
- ❌ Neon/outer glow shadows — use subtle `--accent-glow` ring only on activated graph nodes.
- ❌ Purple/violet accents anywhere.
- ❌ Gradient text (`background-clip: text`) — per `impeccable` absolute ban.
- ❌ Side-stripe borders (`border-left > 1px` as accent) — per `impeccable` absolute ban.
- ❌ Glassmorphism cards — per `impeccable` absolute ban.
- ❌ 3-column identical card grids — per `stitch-design-taste`.
- ❌ Rounded corners > 4px — sharp edges define the "Terminal Scholar" identity.
- ❌ Google Fonts CDN — all fonts self-hosted.

### UX Bans
- ❌ Placeholder-only labels — per `ui-ux-pro-max` §8.
- ❌ Hover-only interactions — per `ui-ux-pro-max` §2.
- ❌ Jumpy progress bars — smooth anime.js transitions only.
- ❌ Generic circular spinners — skeleton shimmer or ASCII loader only.
- ❌ Modal as first thought — exhaust inline options first.
- ❌ `space-y-*` or `space-x-*` — use flex with `gap-*` to prevent layout bugs.

### Copy Bans
- ❌ "Elevate", "Seamless", "Unleash", "Next-Gen".
- ❌ "Scroll to explore", scroll arrows, bouncing chevrons.
- ❌ "John Doe", "Acme", "Lorem Ipsum".
- ❌ Em dashes — use commas, colons, semicolons.

---

## 10. Design Skills Reference

The following core AI developer skills and design philosophies were utilized to establish the design tokens and layout boundaries:

| Skill Name | Role & Influence in Design System |
|---|---|
| `frontend-design` | Formulated the "Terminal Scholar" visual theme, distinct font pairings, and canvas background grid patterns. |
| `ui-ux-pro-max` | Established screen breakpoints, touch target margins, layout z-index orders, skeleton screen timings, and tabular mono alignment rules. |
| `design-md` | Structured this document layout (atmosphere, palette, typography rules, layout models, and features specs). |
| `stitch-design-taste` | Scored atmospheric density, limited accent saturation (<80%, Mineral Teal), established spring motion variables, and specified typography/visual bans. |
| `shadcn` | Guided Tailwind-based primitive mapping and styling compositions using semantic classes instead of hardcoded hex values. |
| `impeccable` | Defined the dark atmosphere scene sentence, OKLCH neutral tint offsets, copy guidelines, and prohibited common UI shortcuts (glassmorphic cards, gradient text). |

---

## 11. MCP Server Design Knowledge

These MCP tools were leveraged to build, preview, and refine the user interface layout:

### 11.1 Stitch (Google Stitch)
*   **Design-to-Code Reference**: Screen designs inside the "Private Local PDF RAG" Stitch project were used as the primary HTML/Tailwind skeleton references.
*   **Design System Mapping**: Synced design token parameters (Mineral Teal, Charcoal Void, Space Grotesk) to Stitch to align preview screens with the actual code variables.

### 11.2 shadcn (Component Registry)
*   **Component Discovery**: Searched registries for collapsible, sidebar, and resizable layout components.
*   **Prop Alignments**: Leveraged registry templates to inspect appropriate props, states, and accessibility bindings before styling.

### 11.3 Magic / 21st.dev
*   **Tailwind Widgets**: Used the component generator to build initial tailwind setups for the ASCII loading screen, mouse-reactive grid canvas, and monospaced drag-zones.
