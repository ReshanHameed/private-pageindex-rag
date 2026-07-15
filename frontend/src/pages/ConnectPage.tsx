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
  const sep = info.project_root.includes('\\') ? '\\' : '/';
  const dataDir = `${info.project_root}${sep}data`;
  return JSON.stringify(
    {
      mcpServers: {
        'private-pageindex-rag': {
          command: info.stdio.command,
          args: info.stdio.args,
          cwd: info.stdio.cwd,
          env: {
            DATA_DIR: dataDir,
            INBOX_DIR: info.inbox_dir,
          },
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
    <div className="w-full h-full overflow-y-auto no-scrollbar animate-fade-in pb-10">
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
