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
