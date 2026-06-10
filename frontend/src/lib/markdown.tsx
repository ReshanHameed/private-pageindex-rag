import React from 'react';
import CitationLink from '@/components/chat/CitationLink';

/**
 * Splits text into inline bold and citation elements.
 */
export function parseInlineElements(
  text: string,
  onCitationClick?: (pageNum: number) => void
): React.ReactNode[] {
  // First, parse bold segments: **bold**
  const boldRegex = /(\*\*.*?\*\*)/g;
  const parts = text.split(boldRegex);

  return parts.flatMap((part, partIdx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const boldText = part.slice(2, -2);
      return (
        <strong key={`bold-${partIdx}`} className="text-text-primary font-bold">
          {parseCitations(boldText, onCitationClick)}
        </strong>
      );
    }
    return parseCitations(part, onCitationClick);
  });
}

/**
 * Splits text into normal text and interactive CitationLink badges.
 */
export function parseCitations(
  text: string,
  onCitationClick?: (pageNum: number) => void
): React.ReactNode[] {
  // Matches citation variants: [page N], Page N, (page N), etc. case-insensitively
  const citationRegex = /(\[?[pP]ages?\s+\d+(?:-\d+)?\]?|\(?[pP]ages?\s+\d+(?:-\d+)?\)?)/g;
  const parts = text.split(citationRegex);

  return parts.map((part, idx) => {
    const match = part.match(/[pP]ages?\s+(\d+)/);
    if (match) {
      const pageNum = parseInt(match[1], 10);
      return (
        <CitationLink
          key={`cite-${idx}`}
          pageNumber={pageNum}
          onClick={() => onCitationClick?.(pageNum)}
        />
      );
    }
    return part;
  });
}

/**
 * Main parser that splits text into block-level elements (headings, lists, paragraphs)
 * and processes inline bolding and citations inside them.
 */
export function renderStructuredAnswer(
  text: string,
  onCitationClick?: (pageNum: number) => void
): React.ReactNode {
  if (!text) return null;

  const lines = text.split('\n');
  const renderedElements: React.ReactNode[] = [];

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    // Headers
    if (line.startsWith('### ')) {
      renderedElements.push(
        <h3
          key={`h3-${lineIdx}`}
          className="text-accent font-display text-sm font-bold mt-4 mb-2 tracking-wide uppercase flex items-center gap-1.5"
        >
          <span className="text-[10px] opacity-65 select-none font-mono">///</span>
          {parseInlineElements(line.substring(4), onCitationClick)}
        </h3>
      );
      return;
    }
    if (line.startsWith('## ')) {
      renderedElements.push(
        <h2
          key={`h2-${lineIdx}`}
          className="text-accent font-display text-[15px] font-bold mt-5 mb-3 tracking-wider uppercase flex items-center gap-1.5"
        >
          <span className="text-[11px] opacity-65 select-none font-mono">//</span>
          {parseInlineElements(line.substring(3), onCitationClick)}
        </h2>
      );
      return;
    }
    if (line.startsWith('# ')) {
      renderedElements.push(
        <h1
          key={`h1-${lineIdx}`}
          className="text-accent font-display text-base font-bold mt-6 mb-4 tracking-widest uppercase flex items-center gap-1.5"
        >
          <span className="text-[12px] opacity-65 select-none font-mono">/</span>
          {parseInlineElements(line.substring(2), onCitationClick)}
        </h1>
      );
      return;
    }

    // Bulleted lists (e.g. "- Item" or "* Item")
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      // Find indentation depth
      const marker = trimmed.startsWith('- ') ? '- ' : '* ';
      const indentIndex = line.indexOf(marker.trim());
      const paddingLeft = Math.max(16, (indentIndex + 1) * 12);
      
      renderedElements.push(
        <div
          key={`bullet-${lineIdx}`}
          className="flex items-start gap-2 my-1.5 leading-relaxed"
          style={{ paddingLeft: `${paddingLeft}px` }}
        >
          <span className="text-accent select-none font-mono text-[10px] mt-1 shrink-0">▪</span>
          <span className="flex-1 text-text-secondary text-sm">
            {parseInlineElements(trimmed.substring(2), onCitationClick)}
          </span>
        </div>
      );
      return;
    }

    // Numbered lists (e.g. "1. Item")
    const numMatch = trimmed.match(/^(\d+)\.\s(.*)/);
    if (numMatch) {
      const num = numMatch[1];
      const content = numMatch[2];
      const indentIndex = line.indexOf(num);
      const paddingLeft = Math.max(8, (indentIndex + 1) * 8);

      renderedElements.push(
        <div
          key={`num-${lineIdx}`}
          className="flex items-start gap-2 my-1.5 leading-relaxed"
          style={{ paddingLeft: `${paddingLeft}px` }}
        >
          <span className="text-accent font-mono font-bold select-none text-[12px] shrink-0">{num}.</span>
          <span className="flex-1 text-text-secondary text-sm">
            {parseInlineElements(content, onCitationClick)}
          </span>
        </div>
      );
      return;
    }

    // Empty lines (render as paragraph separation gap)
    if (trimmed === '') {
      renderedElements.push(<div key={`space-${lineIdx}`} className="h-3 select-none" />);
      return;
    }

    // Default Paragraph line
    renderedElements.push(
      <p
        key={`p-${lineIdx}`}
        className="my-1.5 text-text-secondary text-sm leading-relaxed"
      >
        {parseInlineElements(line, onCitationClick)}
      </p>
    );
  });

  return <div className="flex flex-col">{renderedElements}</div>;
}
