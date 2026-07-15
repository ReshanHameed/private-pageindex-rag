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
