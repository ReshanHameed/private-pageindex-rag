import { useState, type FormEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
}

export default function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSubmit(input.trim());
    setInput('');
  };

  return (
    <form onSubmit={handleSubmit} className="p-3 border-t border-border-dim bg-bg-void/60 flex flex-col gap-1.5 shrink-0">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about this document..."
          disabled={isLoading}
          aria-label="Ask a question about this document"
          className="flex-1 bg-bg-surface border border-border-default px-3 py-2.5 text-sm font-sans text-text-primary placeholder:font-mono placeholder:text-xs placeholder:text-text-tertiary focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent focus:border-accent/50 transition-colors disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          aria-label="Submit question"
          className="p-2.5 border border-border-default bg-bg-surface text-text-secondary hover:bg-accent hover:text-bg-void hover:border-accent/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-50 disabled:hover:text-text-secondary disabled:hover:bg-bg-surface disabled:hover:border-border-default transition-all cursor-pointer"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </button>
      </div>
    </form>
  );
}
