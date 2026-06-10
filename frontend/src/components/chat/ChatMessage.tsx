import { Bot, User, CornerDownRight } from 'lucide-react';
import type { ChatRecord } from '@/lib/types';
import { Link } from 'react-router-dom';
import { renderStructuredAnswer } from '@/lib/markdown';

interface ChatMessageProps {
  chat: ChatRecord;
  docId: string;
  onCitationClick?: (pageNum: number) => void;
}

export default function ChatMessage({ chat, docId, onCitationClick }: ChatMessageProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* User Question */}
      <div className="flex flex-row-reverse gap-3 items-start">
        <div className="w-6 h-6 shrink-0 bg-bg-interactive border border-border-dim flex items-center justify-center text-text-secondary mt-1">
          <User className="w-3 h-3" />
        </div>
        <div className="flex-1 flex flex-col gap-1 items-end max-w-[85%] ml-auto">
          <span className="font-mono text-[10px] text-text-tertiary uppercase">User</span>
          <div className="text-sm font-sans text-text-primary leading-relaxed bg-bg-interactive border border-border-dim p-3 w-full">
            {chat.question}
          </div>
        </div>
      </div>

      {/* Assistant Answer */}
      <div className="flex gap-3">
        <div className="w-6 h-6 shrink-0 bg-accent-ghost border border-accent/20 flex items-center justify-center text-accent mt-1">
          <Bot className="w-3 h-3" />
        </div>
        <div className="flex-1 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-accent uppercase font-bold">Assistant</span>
            <Link 
              to={`/documents/${docId}/chats/${chat.id}/trace`}
              className="font-mono text-[10px] text-text-tertiary hover:text-accent transition-colors flex items-center gap-1"
            >
              <CornerDownRight className="w-3 h-3" /> VIEW_TRACE
            </Link>
          </div>
          <div className="text-sm font-sans text-text-primary leading-relaxed bg-bg-surface border border-border-dim p-3 whitespace-pre-wrap">
            {renderStructuredAnswer(chat.answer, onCitationClick)}
          </div>
        </div>
      </div>
    </div>
  );
}
