import type { TraceStep } from '@/lib/types';

interface TraceTimelineProps {
  steps: TraceStep[];
}

/** Map pipeline step actions to semantic color classes */
function stepColor(action: string): string {
  switch (action) {
    case 'inspect_tree':
      return 'text-text-secondary';
    case 'select_nodes':
      return 'text-accent';
    case 'fetch_pages':
      return 'text-info';
    case 'generate_answer':
      return 'text-success';
    default:
      return 'text-accent';
  }
}

export default function TraceTimeline({ steps }: TraceTimelineProps) {
  if (!steps || steps.length === 0) return <div className="text-text-tertiary">No trace steps found.</div>;

  const formatTime = (timeStr?: string) => {
    if (!timeStr) return '--:--:--';
    try {
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) return '--:--:--';
      return date.toISOString().split('T')[1].substring(0, 8);
    } catch {
      return '--:--:--';
    }
  };

  return (
    <div className="flex flex-col gap-0 font-mono text-xs w-full max-w-3xl mx-auto">
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        const color = stepColor(step.action);

        return (
          <div key={idx} className="flex flex-col">
            <div className="flex items-start gap-4">
              {/* Timeline marker */}
              <div className="flex flex-col items-center shrink-0 w-8">
                <div className="size-2 bg-accent" />
                {!isLast && <div className="w-px h-full min-h-[40px] bg-border-dim my-1" />}
              </div>

              {/* Step content */}
              <div className="flex-1 pb-6 pt-0 mt-[-4px]">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`font-bold uppercase ${color}`}>{step.action}</span>
                  <span className="text-text-tertiary text-[10px] font-mono tabular-nums">{formatTime(step.created_at)}</span>
                </div>
                
                <div className="bg-bg-surface border border-border-dim p-3 text-text-secondary leading-relaxed">
                  <div className="mb-2 text-text-primary">{step.reason}</div>
                  
                  {(step.node_id || step.pages) && (
                    <div className="flex gap-4 mt-3 pt-3 border-t border-border-dim text-[10px]">
                      {step.node_id && (
                        <div>
                          <span className="text-text-tertiary uppercase mr-2">Node:</span>
                          <span className="bg-bg-interactive px-1 py-0.5 font-mono tabular-nums">{step.node_id}</span>
                        </div>
                      )}
                      {step.pages && (
                        <div>
                          <span className="text-text-tertiary uppercase mr-2">Pages:</span>
                          <span className="bg-bg-interactive px-1 py-0.5 font-mono tabular-nums">
                            {Array.isArray(step.pages) ? step.pages.join(', ') : String(step.pages)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

