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
