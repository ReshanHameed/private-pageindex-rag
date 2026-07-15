import type { McpInfo, McpHttpStatus } from '../../lib/types';

interface McpStatusBarProps {
  info: McpInfo | null;
  httpStatus: McpHttpStatus | null;
}

export default function McpStatusBar({ info, httpStatus }: McpStatusBarProps) {
  const toolCount = info?.tools.length ?? 0;
  const authOn = info?.http.auth_required ?? false;
  const httpRunning = httpStatus?.running ?? false;
  const stdioReady = info?.installed ?? false;

  return (
    <div className="border border-border-dim bg-bg-surface">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 font-mono text-[11px]">
        <span className="text-text-secondary">
          MCP:{' '}
          {stdioReady ? (
            <span className="text-success">installed</span>
          ) : (
            <span className="text-error">not installed</span>
          )}
        </span>
        <span className="text-text-secondary">
          Tools: <span className="text-accent font-bold">{toolCount}</span>
        </span>
        <span className="text-text-secondary">
          stdio:{' '}
          {stdioReady ? (
            <span className="text-success">&#9679; available</span>
          ) : (
            <span className="text-text-tertiary">&#9675; unavailable</span>
          )}
        </span>
        <span className="text-text-secondary">
          HTTP:{' '}
          {httpRunning ? (
            <span className="text-success">&#9679; running</span>
          ) : (
            <span className="text-text-tertiary">&#9675; not running</span>
          )}
          {info && <span className="text-text-tertiary"> ({info.http.url})</span>}
        </span>
        <span className="text-text-secondary">
          HTTP auth:{' '}
          <span className={authOn ? 'text-warning' : 'text-text-tertiary'}>
            {authOn ? 'on' : 'off'}
          </span>
        </span>
      </div>
      <p className="border-t border-border-dim px-4 py-2 font-mono text-[10px] leading-relaxed text-text-tertiary">
        Claude Desktop and Cursor use <span className="text-text-secondary">stdio</span> — each
        client launches its own MCP process, so stdio shows available when the package is
        installed. HTTP and HTTP auth apply only to the optional shared server started with{' '}
        <span className="text-accent">serve-mcp --http</span>.
      </p>
    </div>
  );
}
