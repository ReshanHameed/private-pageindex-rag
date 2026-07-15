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
