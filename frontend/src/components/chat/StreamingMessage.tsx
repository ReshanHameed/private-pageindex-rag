import { useEffect, useRef } from 'react';
import { Bot } from 'lucide-react';
import { renderStructuredAnswer } from '@/lib/markdown';

interface StreamingMessageProps {
  streamedAnswer: string;
  isStreaming: boolean;
  onCitationClick?: (pageNum: number) => void;
}

/**
 * Renders a streaming answer with a blinking cursor while tokens arrive.
 * Citation patterns like [page 5] are converted to interactive CitationLink
 * components after the stream completes.
 */
export default function StreamingMessage({
  streamedAnswer,
  isStreaming,
  onCitationClick,
}: StreamingMessageProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [streamedAnswer]);

  // Parse citations from completed answer
  const renderAnswer = () => {
    if (!streamedAnswer) return null;

    if (isStreaming) {
      // While streaming, show raw text with blinking cursor. Newlines are preserved by whitespace-pre-wrap on parent div
      return (
        <>
          {streamedAnswer}
          <span className="inline-block w-[2px] h-4 bg-accent ml-0.5 align-text-bottom animate-[cursor-blink_1s_steps(2)_infinite]" />
        </>
      );
    }

    return renderStructuredAnswer(streamedAnswer, onCitationClick);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* The question is shown in DocumentPage, so only show the answer here */}
      <div className="flex gap-3">
        <div className="w-6 h-6 shrink-0 bg-accent-ghost border border-accent/20 flex items-center justify-center text-accent mt-1">
          <Bot className="w-3 h-3" />
        </div>
        <div className="flex-1 flex flex-col gap-2">
          <span className="font-mono text-[10px] text-accent uppercase font-bold">
            Assistant {isStreaming && <span className="text-text-tertiary ml-2">STREAMING</span>}
          </span>
          <div className="text-sm font-sans text-text-primary leading-relaxed bg-bg-surface border border-border-dim p-3 whitespace-pre-wrap" aria-live="polite" aria-atomic="false">
            {renderAnswer()}
          </div>
        </div>
      </div>
      <div ref={endRef} />
    </div>
  );
}
