# MCP Connect Screen Implementation Plan

> **For agentic workers:** Implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Backend tasks are TDD (test first). Frontend has no JS test runner, so frontend verification is `npx tsc --noEmit`, `npm run lint`, and `npm run build`.

**Goal:** Add an in-app "Connect" screen that lets external agents (Claude Desktop, Cursor, Codex, Antigravity IDE, and manual MCP clients) connect to the local MCP server, with a live read-only status/tools panel.

**Architecture:** Two read-only FastAPI endpoints (`/api/mcp/info`, `/api/mcp/http-status`) expose MCP config + the live tool catalog; a new lazy-loaded React page (`/connect`) generates per-agent config snippets client-side and renders agent cards, a status bar, and a tool catalog.

**Tech Stack:** FastAPI, httpx, the `mcp` FastMCP registry (backend); React 19 + TypeScript + Tailwind v4 + lucide-react + sonner (frontend). Spec: `docs/superpowers/specs/2026-07-14-mcp-connect-screen-design.md`.

---

## Task 1: Backend — `/api/mcp/info` endpoint

**Files:**
- Modify: `private_pageindex/web/app.py` (add route near the other `/api/*` routes, before the SPA catch-all block)
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_web_app.py`:

```python
def test_api_mcp_info_returns_transports_and_tools():
    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/api/mcp/info")
        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        # transport config
        assert data["stdio"]["args"] == ["-m", "private_pageindex.cli", "serve-mcp"]
        assert data["stdio"]["cwd"]
        assert data["http"]["url"].endswith("/mcp")
        assert isinstance(data["http"]["auth_required"], bool)
        assert data["inbox_dir"]
        # tool catalog read from the FastMCP registry
        tool_names = {t["name"] for t in data["tools"]}
        assert "ingest_pdf" in tool_names
        assert "ask" in tool_names
        assert "list_documents" in tool_names
    finally:
        teardown_test_app(web_module, orig)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_api_mcp_info_returns_transports_and_tools -v`
Expected: FAIL with 404 (route not defined).

- [ ] **Step 3: Write minimal implementation**

In `private_pageindex/web/app.py`, add this route immediately after the existing `api_delete_document_rest` route (before the `# SPA Static Serving` section):

```python
@app.get("/api/mcp/info", response_class=JSONResponse)
async def api_mcp_info():
    """Return MCP server connection info and the tool catalog (read-only)."""
    import sys

    settings = get_settings()
    root = Path(__file__).resolve().parent.parent.parent
    python_exe = sys.executable
    host = settings.mcp_http_host
    port = settings.mcp_http_port
    auth_required = bool((settings.mcp_auth_token or "").strip())

    installed = True
    tools_payload: list[dict[str, str]] = []
    try:
        from private_pageindex.mcp_server import mcp as mcp_app

        tool_list = await mcp_app.list_tools()
        tools_payload = [
            {"name": t.name, "description": (t.description or "").strip()}
            for t in tool_list
        ]
    except ModuleNotFoundError:
        installed = False

    return {
        "installed": installed,
        "project_root": str(root),
        "python_executable": python_exe,
        "stdio": {
            "command": python_exe,
            "args": ["-m", "private_pageindex.cli", "serve-mcp"],
            "cwd": str(root),
        },
        "http": {
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}/mcp",
            "auth_required": auth_required,
        },
        "inbox_dir": str(settings.inbox_dir),
        "tools": tools_payload,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_api_mcp_info_returns_transports_and_tools -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add private_pageindex/web/app.py tests/test_web_app.py
git commit -m "feat: add /api/mcp/info endpoint for MCP connect screen"
```

---

## Task 2: Backend — `/api/mcp/http-status` endpoint

**Files:**
- Modify: `private_pageindex/web/app.py` (add route right after `api_mcp_info`)
- Test: `tests/test_web_app.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_web_app.py`:

```python
def test_api_mcp_http_status_running(monkeypatch):
    class _FakeResp:
        status_code = 406

    class _FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return _FakeResp()

    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)

    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/api/mcp/http-status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is True
        assert data["url"].endswith("/mcp")
        assert "406" in data["detail"]
    finally:
        teardown_test_app(web_module, orig)


def test_api_mcp_http_status_not_running(monkeypatch):
    import httpx

    class _FailAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("httpx.AsyncClient", _FailAsyncClient)

    client, storage, test_dir, web_module, orig = make_test_app()
    try:
        response = client.get("/api/mcp/http-status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
    finally:
        teardown_test_app(web_module, orig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_api_mcp_http_status_running tests/test_web_app.py::test_api_mcp_http_status_not_running -v`
Expected: FAIL with 404 (route not defined).

- [ ] **Step 3: Write minimal implementation**

In `private_pageindex/web/app.py`, add immediately after `api_mcp_info`:

```python
@app.get("/api/mcp/http-status", response_class=JSONResponse)
async def api_mcp_http_status():
    """Probe the configured streamable-HTTP MCP endpoint for reachability."""
    import httpx

    settings = get_settings()
    url = f"http://{settings.mcp_http_host}:{settings.mcp_http_port}/mcp"
    try:
        async with httpx.AsyncClient(timeout=2.0) as probe:
            resp = await probe.get(url)
        return {"running": True, "url": url, "detail": f"HTTP {resp.status_code}"}
    except httpx.ConnectError:
        return {"running": False, "url": url, "detail": "Connection refused"}
    except httpx.TimeoutException:
        return {"running": False, "url": url, "detail": "Timed out"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"running": False, "url": url, "detail": str(exc)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_web_app.py::test_api_mcp_http_status_running tests/test_web_app.py::test_api_mcp_http_status_not_running -v`
Expected: PASS (both)

- [ ] **Step 5: Commit**

```bash
git add private_pageindex/web/app.py tests/test_web_app.py
git commit -m "feat: add /api/mcp/http-status reachability probe"
```

---

## Task 3: Frontend — types and API methods

**Files:**
- Modify: `frontend/src/lib/types.ts` (append)
- Modify: `frontend/src/lib/api.ts` (add two methods to the `api` object)

- [ ] **Step 1: Add types**

Append to `frontend/src/lib/types.ts`:

```ts
export interface McpTool {
  name: string;
  description: string;
}

export interface McpTransportStdio {
  command: string;
  args: string[];
  cwd: string;
}

export interface McpTransportHttp {
  host: string;
  port: number;
  url: string;
  auth_required: boolean;
}

export interface McpInfo {
  installed: boolean;
  project_root: string;
  python_executable: string;
  stdio: McpTransportStdio;
  http: McpTransportHttp;
  inbox_dir: string;
  tools: McpTool[];
}

export interface McpHttpStatus {
  running: boolean;
  url: string;
  detail: string;
}
```

- [ ] **Step 2: Add API methods**

In `frontend/src/lib/api.ts`, add these two methods inside the `api` object (e.g. after `deleteSession`):

```ts
  async getMcpInfo(): Promise<import('./types').McpInfo> {
    const res = await fetch('/api/mcp/info');
    if (!res.ok) {
      throw new Error(`Failed to fetch MCP info: ${res.statusText}`);
    }
    return res.json();
  },

  async getMcpHttpStatus(): Promise<import('./types').McpHttpStatus> {
    const res = await fetch('/api/mcp/http-status');
    if (!res.ok) {
      throw new Error(`Failed to fetch MCP HTTP status: ${res.statusText}`);
    }
    return res.json();
  },
```

Note: place a comma after the previous method and ensure the added methods keep the object valid.

- [ ] **Step 3: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add MCP info/status types and API client methods"
```

---

## Task 4: Frontend — `ConfigBlock` component

**Files:**
- Create: `frontend/src/components/connect/ConfigBlock.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface ConfigBlockProps {
  code: string;
  label?: string;
}

export default function ConfigBlock({ code, label }: ConfigBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="relative mt-3 border border-border-dim bg-bg-void">
      {label && (
        <div className="px-3 py-1.5 border-b border-border-dim font-mono text-[10px] uppercase tracking-widest text-text-tertiary">
          {label}
        </div>
      )}
      <button
        onClick={handleCopy}
        aria-label="Copy configuration"
        className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 font-mono text-[10px] uppercase tracking-wide text-text-secondary hover:text-accent border border-border-default hover:border-accent bg-bg-surface transition-colors cursor-pointer"
      >
        {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className="overflow-x-auto p-3 pt-9 font-mono text-[11px] leading-relaxed text-text-primary whitespace-pre">
        {code}
      </pre>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/connect/ConfigBlock.tsx
git commit -m "feat: add ConfigBlock copy-to-clipboard component"
```

---

## Task 5: Frontend — `AgentCard` component

**Files:**
- Create: `frontend/src/components/connect/AgentCard.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Check, ChevronDown } from 'lucide-react';
import ConfigBlock from './ConfigBlock';

export interface AgentAction {
  label: string;
  href?: string;
  onClick?: () => void;
}

interface AgentCardProps {
  icon: LucideIcon;
  name: string;
  features: string[];
  config?: string;
  configLabel?: string;
  actions?: AgentAction[];
  recommended?: boolean;
}

export default function AgentCard({
  icon: Icon,
  name,
  features,
  config,
  configLabel,
  actions,
  recommended,
}: AgentCardProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-border-default bg-bg-surface p-4 flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-accent" />
          <h3 className="font-display font-bold text-sm text-text-primary">{name}</h3>
        </div>
        {recommended && (
          <span className="font-mono text-[9px] uppercase tracking-widest text-success border border-success/50 px-1.5 py-0.5">
            Recommended
          </span>
        )}
      </div>

      <ul className="mt-3 space-y-1">
        {features.map((f) => (
          <li key={f} className="flex items-center gap-2 font-mono text-[11px] text-text-secondary">
            <Check className="w-3 h-3 text-success shrink-0" />
            {f}
          </li>
        ))}
      </ul>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {config && (
          <button
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-1 px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-text-secondary hover:text-accent border border-border-default hover:border-accent bg-bg-interactive transition-colors cursor-pointer"
          >
            <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
            {open ? 'Hide config' : 'Show config'}
          </button>
        )}
        {actions?.map((a) =>
          a.href ? (
            <a
              key={a.label}
              href={a.href}
              className="px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-accent border border-accent hover:bg-accent hover:text-bg-void transition-colors cursor-pointer"
            >
              {a.label}
            </a>
          ) : (
            <button
              key={a.label}
              onClick={a.onClick}
              className="px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-accent border border-accent hover:bg-accent hover:text-bg-void transition-colors cursor-pointer"
            >
              {a.label}
            </button>
          )
        )}
      </div>

      {config && open && <ConfigBlock code={config} label={configLabel} />}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/connect/AgentCard.tsx
git commit -m "feat: add AgentCard component for the connect hub"
```

---

## Task 6: Frontend — `McpStatusBar` component

**Files:**
- Create: `frontend/src/components/connect/McpStatusBar.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { McpInfo, McpHttpStatus } from '../../lib/types';

interface McpStatusBarProps {
  info: McpInfo | null;
  httpStatus: McpHttpStatus | null;
}

export default function McpStatusBar({ info, httpStatus }: McpStatusBarProps) {
  const toolCount = info?.tools.length ?? 0;
  const authOn = info?.http.auth_required ?? false;
  const running = httpStatus?.running ?? false;

  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border border-border-dim bg-bg-surface px-4 py-3 font-mono text-[11px]">
      <span className="text-text-secondary">
        MCP:{' '}
        {info?.installed ? (
          <span className="text-success">installed</span>
        ) : (
          <span className="text-error">not installed</span>
        )}
      </span>
      <span className="text-text-secondary">
        Tools: <span className="text-accent font-bold">{toolCount}</span>
      </span>
      <span className="text-text-secondary">
        HTTP:{' '}
        {running ? (
          <span className="text-success">&#9679; running</span>
        ) : (
          <span className="text-text-tertiary">&#9675; not running</span>
        )}
        {info && <span className="text-text-tertiary"> ({info.http.url})</span>}
      </span>
      <span className="text-text-secondary">
        Auth:{' '}
        <span className={authOn ? 'text-warning' : 'text-text-tertiary'}>
          {authOn ? 'on' : 'off'}
        </span>
      </span>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/connect/McpStatusBar.tsx
git commit -m "feat: add McpStatusBar read-only status component"
```

---

## Task 7: Frontend — `ToolCatalog` component

**Files:**
- Create: `frontend/src/components/connect/ToolCatalog.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { McpTool } from '../../lib/types';

interface ToolCatalogProps {
  tools: McpTool[];
}

export default function ToolCatalog({ tools }: ToolCatalogProps) {
  if (tools.length === 0) {
    return (
      <p className="font-mono text-[11px] text-text-tertiary">
        No tools available. Install the MCP extra:{' '}
        <span className="text-accent">pip install -e .[mcp]</span>
      </p>
    );
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {tools.map((t) => (
        <div key={t.name} className="border border-border-dim bg-bg-surface p-3">
          <div className="font-mono text-[12px] font-bold text-accent">{t.name}</div>
          <p className="mt-1 font-sans text-[12px] text-text-secondary leading-snug">
            {t.description}
          </p>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run (in `frontend/`): `npx tsc --noEmit`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/connect/ToolCatalog.tsx
git commit -m "feat: add ToolCatalog component listing MCP tools"
```

---

## Task 8: Frontend — `ConnectPage`, route, and sidebar entry

**Files:**
- Create: `frontend/src/pages/ConnectPage.tsx`
- Modify: `frontend/src/App.tsx` (add lazy import + route)
- Modify: `frontend/src/components/layout/AppShell.tsx` (add sidebar item)

- [ ] **Step 1: Create `ConnectPage.tsx`**

```tsx
import { useEffect, useMemo, useState } from 'react';
import {
  MonitorSmartphone,
  MousePointerClick,
  Terminal,
  Rocket,
  Puzzle,
} from 'lucide-react';
import { api } from '../lib/api';
import type { McpInfo, McpHttpStatus } from '../lib/types';
import McpStatusBar from '../components/connect/McpStatusBar';
import AgentCard from '../components/connect/AgentCard';
import ToolCatalog from '../components/connect/ToolCatalog';

function buildJsonConfig(info: McpInfo): string {
  return JSON.stringify(
    {
      mcpServers: {
        'private-pageindex-rag': {
          command: info.stdio.command,
          args: info.stdio.args,
          cwd: info.stdio.cwd,
        },
      },
    },
    null,
    2
  );
}

function buildTomlConfig(info: McpInfo): string {
  const args = info.stdio.args.map((a) => `"${a}"`).join(', ');
  const esc = (s: string) => s.replace(/\\/g, '\\\\');
  return [
    '[mcp_servers.private-pageindex-rag]',
    `command = "${esc(info.stdio.command)}"`,
    `args = [${args}]`,
    `cwd = "${esc(info.stdio.cwd)}"`,
  ].join('\n');
}

function buildCursorDeeplink(info: McpInfo): string {
  const cfg = {
    command: info.stdio.command,
    args: info.stdio.args,
    cwd: info.stdio.cwd,
  };
  const b64 = btoa(JSON.stringify(cfg));
  return `cursor://anysphere.cursor-deeplink/mcp/install?name=private-pageindex-rag&config=${encodeURIComponent(
    b64
  )}`;
}

function buildHttpConfig(info: McpInfo): string {
  return JSON.stringify(
    { mcpServers: { 'private-pageindex-rag': { url: info.http.url } } },
    null,
    2
  );
}

function buildManualCommands(info: McpInfo): string {
  const cmd = `${info.stdio.command} -m private_pageindex.cli serve-mcp`;
  return [
    '# stdio (per-agent):',
    cmd,
    '',
    '# streamable HTTP (shared instance):',
    `${cmd} --http --host ${info.http.host} --port ${info.http.port}`,
    `# endpoint: ${info.http.url}`,
  ].join('\n');
}

export default function ConnectPage() {
  const [info, setInfo] = useState<McpInfo | null>(null);
  const [httpStatus, setHttpStatus] = useState<McpHttpStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .getMcpInfo()
      .then((d) => active && setInfo(d))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    const poll = () =>
      api
        .getMcpHttpStatus()
        .then((d) => active && setHttpStatus(d))
        .catch(() => {});
    poll();
    const id = setInterval(poll, 10000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const configs = useMemo(() => {
    if (!info) return null;
    return {
      json: buildJsonConfig(info),
      toml: buildTomlConfig(info),
      cursorDeeplink: buildCursorDeeplink(info),
      http: buildHttpConfig(info),
      manual: buildManualCommands(info),
    };
  }, [info]);

  return (
    <div className="w-full overflow-y-auto animate-fade-in pb-10">
      <header className="mb-6">
        <h1 className="font-display font-bold text-xl text-text-primary tracking-wide uppercase">
          Connect
        </h1>
        <p className="mt-1 font-mono text-xs text-text-secondary">
          Use Private PageIndex RAG with your preferred AI agent via MCP.
        </p>
      </header>

      {error && (
        <div className="mb-4 border border-error/50 bg-error/10 px-4 py-2 font-mono text-[11px] text-error">
          {error}
        </div>
      )}

      <McpStatusBar info={info} httpStatus={httpStatus} />

      <section className="mt-6">
        <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-text-tertiary">
          Agents &amp; Extensions
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <AgentCard
            icon={MonitorSmartphone}
            name="Claude Desktop"
            recommended
            features={['stdio transport', 'Local & online PDFs', 'No Claude Pro required']}
            config={configs?.json}
            configLabel="claude_desktop_config.json"
          />
          <AgentCard
            icon={MousePointerClick}
            name="Cursor"
            features={['One-click install', 'stdio transport', 'Local PDFs']}
            config={configs?.json}
            configLabel=".cursor/mcp.json"
            actions={
              configs
                ? [{ label: 'Add to Cursor', href: configs.cursorDeeplink }]
                : undefined
            }
          />
          <AgentCard
            icon={Terminal}
            name="Codex"
            features={['stdio transport', 'TOML config']}
            config={configs?.toml}
            configLabel="~/.codex/config.toml"
          />
          <AgentCard
            icon={Rocket}
            name="Antigravity IDE"
            features={['Streamable HTTP', 'Shared instance']}
            config={configs?.http}
            configLabel="MCP client config (HTTP)"
          />
          <AgentCard
            icon={Puzzle}
            name="General / Manual"
            features={['stdio + HTTP', 'Any MCP client']}
            config={configs?.manual}
            configLabel="Run commands"
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 font-mono text-[11px] uppercase tracking-widest text-text-tertiary">
          Available Tools ({info?.tools.length ?? 0})
        </h2>
        <ToolCatalog tools={info?.tools ?? []} />
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Add the route in `App.tsx`**

In `frontend/src/App.tsx`, add the lazy import next to the others:

```tsx
const ConnectPage = lazy(() => import('./pages/ConnectPage'));
```

And add the route inside `<Routes>` (before the `*` catch-all):

```tsx
<Route path="/connect" element={<ConnectPage />} />
```

- [ ] **Step 3: Add the sidebar entry in `AppShell.tsx`**

In `frontend/src/components/layout/AppShell.tsx`, add `Plug` to the lucide import:

```tsx
import { Layers, MessageSquare, FilePlus, Database, ChevronRight, Trash2, Plug } from 'lucide-react';
```

Then, immediately after the closing `</SidebarMenu>` of the "Documents Collapsible Category" block (before the "Chat Sessions Section" comment), add an Integrations item:

```tsx
              {/* Integrations */}
              <div className="h-px bg-border-dim mx-2 my-2 group-data-[collapsible=icon]:hidden" />
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    tooltip="Connect"
                    className={`transition-colors ${
                      location.pathname === '/connect'
                        ? '!bg-bg-interactive !text-accent hover:!bg-bg-interactive hover:!text-accent'
                        : 'hover:!bg-bg-interactive hover:!text-accent text-text-secondary'
                    }`}
                  >
                    <Link to="/connect">
                      <Plug className="w-4 h-4 text-accent" />
                      <span className="font-bold tracking-wider uppercase">Connect</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
```

- [ ] **Step 4: Type-check, lint, build**

Run (in `frontend/`):
```bash
npx tsc --noEmit
npm run lint
npm run build
```
Expected: 0 TypeScript errors; lint passes (existing warnings only); build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ConnectPage.tsx frontend/src/App.tsx frontend/src/components/layout/AppShell.tsx
git commit -m "feat: add Connect screen with agent cards, status bar, and tool catalog"
```

---

## Task 9: Docs + full verification

**Files:**
- Modify: `README.md` (mention the in-app Connect screen in the MCP section; bump test count)
- Modify: `docs/ARCHITECTURE.md` (note the two new endpoints and the Connect page)
- Modify: `docs/AGENT_MEMORY.md` (Recent Work Log entry, feature set, invariants)

- [ ] **Step 1: Update README**

In `README.md`, under the "MCP Server" section (after "### Run it" or near "Connecting agents"), add:

```markdown
### In-app Connect screen

The web UI includes a **Connect** screen (sidebar → Connect) that shows the MCP
server status, the live tool catalog, and ready-to-copy connection config for
Claude Desktop, Cursor (one-click "Add to Cursor"), Codex, Antigravity IDE, and
manual MCP clients.
```

Also update the Testing section test count from "129 tests total" to "132 tests total".

- [ ] **Step 2: Update ARCHITECTURE.md**

In `docs/ARCHITECTURE.md`, in the MCP Server Layer section, append:

```markdown
- Web UI: a read-only **Connect** screen (`/connect`) lists connection config per agent and the live tool catalog. It is backed by two read-only endpoints in `web/app.py`: `GET /api/mcp/info` (transports + tool catalog via `mcp.list_tools()`, guarded when `mcp` is not installed) and `GET /api/mcp/http-status` (httpx reachability probe of the shared HTTP endpoint).
```

- [ ] **Step 3: Update AGENT_MEMORY.md**

Add a Recent Work Log entry at the top of the log in `docs/AGENT_MEMORY.md`:

```markdown
### 2026-07-15 - Added in-app MCP Connect screen

What changed:
- Backend: added read-only `GET /api/mcp/info` (transports + tool catalog) and `GET /api/mcp/http-status` (reachability probe) to `web/app.py`.
- Frontend: added `/connect` route and page with a status bar, five agent cards (Claude Desktop, Cursor, Codex, Antigravity, General/Manual) with copy-paste config + Cursor deeplink, and a live tool catalog. Added `components/connect/` (ConfigBlock, AgentCard, McpStatusBar, ToolCatalog), api/types, and a sidebar "Connect" entry.

Files changed:
- `private_pageindex/web/app.py`
- `frontend/src/pages/ConnectPage.tsx` (NEW)
- `frontend/src/components/connect/*` (NEW)
- `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`
- `frontend/src/App.tsx`, `frontend/src/components/layout/AppShell.tsx`
- `tests/test_web_app.py`
- `README.md`, `docs/ARCHITECTURE.md`, `docs/AGENT_MEMORY.md`

Verification:
- Python pytest: 132 passed (129 + 3 new).
- Frontend: `npx tsc --noEmit`, `npm run lint`, `npm run build` all pass.

New invariants:
- `/api/mcp/info` and `/api/mcp/http-status` are read-only (no process control, no token exposure, no `.env` writes).
```

Also update the "Verification Baseline" line to say the suite contains 132 tests.

- [ ] **Step 4: Run the full backend suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: 132 passed.

- [ ] **Step 5: Final frontend verification**

Run (in `frontend/`):
```bash
npx tsc --noEmit
npm run lint
npm run build
```
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/ARCHITECTURE.md docs/AGENT_MEMORY.md
git commit -m "docs: document the in-app MCP Connect screen"
```

---

## Self-Review Notes

- **Spec coverage:** connection hub (Task 8 cards), live read-only status (Tasks 2, 6), tool catalog (Tasks 1, 7), five agent cards (Task 8), thin backend (Tasks 1-2), types/api (Task 3), styling via Terminal Scholar tokens (Tasks 4-8), testing (Tasks 1-2 backend + frontend build checks), docs (Task 9). All spec sections mapped.
- **Type consistency:** `McpInfo`, `McpTool`, `McpHttpStatus`, `McpTransportStdio`, `McpTransportHttp` defined in Task 3 and used consistently in Tasks 6-8. `AgentCard` props (`config`, `configLabel`, `actions`, `recommended`) defined in Task 5 and used in Task 8. Endpoint response shapes in Tasks 1-2 match the frontend types in Task 3.
- **Out of scope confirmed:** no inbox UI, no process control, no token rotation.
