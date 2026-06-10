import { useEffect, useRef } from 'react';
import { animate } from 'animejs';
import { prefersReducedMotion } from '@/lib/motion';

interface ThinkingIndicatorProps {
  step?: string | null;
}

const STEP_LABELS: Record<string, string> = {
  inspect_tree: 'INSPECTING_TREE',
  select_nodes: 'SELECTING_NODES',
  fetch_pages: 'FETCHING_PAGES',
  context_ready: 'CONTEXT_LOADED',
  generating: 'GENERATING_ANSWER',
  lexical_fallback: 'LEXICAL_FALLBACK',
  page_text_fallback: 'PAGE_TEXT_SEARCH',
  overview_expansion: 'EXPANDING_SCOPE',
  sibling_expansion: 'EXPANDING_SIBLINGS',
};

export default function ThinkingIndicator({ step }: ThinkingIndicatorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hasAnimatedRef = useRef(false);

  useEffect(() => {
    if (!containerRef.current || hasAnimatedRef.current || prefersReducedMotion()) return;
    hasAnimatedRef.current = true;

    const chars = containerRef.current.querySelectorAll('.thinking-char');
    if (chars.length === 0) return;

    animate(chars, {
      opacity: [0.3, 1, 0.3],
      loop: true,
      duration: 1200,
      delay: (_el: Element, i: number) => i * 80,
      easing: 'easeInOutSine',
    });
  }, []);

  const label = step ? STEP_LABELS[step] || step.toUpperCase() : 'PROCESSING';

  return (
    <div ref={containerRef} className="flex items-center gap-3 py-2">
      <div className="flex items-center gap-0.5 font-mono text-sm text-accent select-none" aria-label="Processing">
        {'▒░▓'.split('').map((c, i) => (
          <span key={`l-${i}`} className="thinking-char">{c}</span>
        ))}
        <span className="thinking-char mx-1.5 text-text-secondary">{label}</span>
        {'▓░▒'.split('').map((c, i) => (
          <span key={`r-${i}`} className="thinking-char">{c}</span>
        ))}
      </div>
    </div>
  );
}
