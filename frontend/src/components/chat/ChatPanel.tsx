import { useRef, useEffect } from 'react';
import { MessageSquare, Loader2, User, Bot, Plus } from 'lucide-react';
import type { ChatRecord } from '@/lib/types';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { useStreamStore } from '../../lib/traceStore';
import { useAppStore } from '../../lib/store';
import StreamingMessage from './StreamingMessage';
import ThinkingIndicator from './ThinkingIndicator';

interface ChatPanelProps {
  chats: ChatRecord[];
  onAsk: (question: string) => Promise<void>;
  isLoading: boolean;
  docId: string;
  onCitationClick?: (pageNum: number) => void;
}

export default function ChatPanel({ chats, onAsk, isLoading, docId, onCitationClick }: ChatPanelProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const { isStreaming, streamedAnswer, currentStep, question } = useStreamStore();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chats, isLoading, isStreaming, streamedAnswer]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header bar */}
      <div className="p-3 border-b border-border-dim bg-bg-void/60 flex items-center justify-between select-none shrink-0">
        <span className="font-mono text-xs font-bold text-text-secondary flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-accent" /> TREE_SEARCH_CHAT
        </span>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] text-text-tertiary hidden sm:inline">
            LOCAL_OLLAMA_INFERENCE
          </span>
          <button 
            onClick={() => {
              const store = useAppStore.getState();
              store.setActiveSessionId(null);
              store.setCurrentChats([]);
            }}
            className="flex items-center gap-1.5 px-2 py-1 bg-bg-surface hover:bg-bg-interactive text-text-secondary hover:text-accent border border-border-dim transition-colors"
            title="New Chat Session"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="font-mono text-[10px] uppercase font-bold tracking-wider">New Chat</span>
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 custom-scrollbar bg-bg-void/30">
        {chats.length === 0 && !isStreaming ? (
          <div className="text-center text-text-tertiary my-auto select-none font-mono text-xs max-w-xs mx-auto">
            <MessageSquare className="w-8 h-8 mx-auto mb-3 text-text-tertiary/40" />
            <p>No chat history.</p>
            <p className="mt-2 text-text-tertiary/60">Ask a question to trigger a tree-guided retrieval over this document.</p>
          </div>
        ) : (
          <>
            {[...chats].reverse().map((chat) => (
              <ChatMessage 
                key={chat.id} 
                chat={chat} 
                docId={docId} 
                onCitationClick={onCitationClick}
              />
            ))}

            {/* Live Streaming Message Box */}
            {isStreaming && (
              <div className="flex flex-col gap-4 border-t border-dashed border-border-dim pt-4">
                {/* User Message */}
                <div className="flex flex-row-reverse gap-3 items-start">
                  <div className="w-6 h-6 shrink-0 bg-bg-interactive border border-border-dim flex items-center justify-center text-text-secondary mt-1">
                    <User className="w-3 h-3" />
                  </div>
                  <div className="flex-1 flex flex-col gap-1 items-end max-w-[85%] ml-auto">
                    <span className="font-mono text-[10px] text-text-tertiary uppercase">User</span>
                    <div className="text-sm font-sans text-text-primary leading-relaxed bg-bg-interactive/40 border border-border-dim p-3 w-full">
                      {question}
                    </div>
                  </div>
                </div>

                {/* Assistant Message (Thinking vs Streaming) */}
                {streamedAnswer ? (
                  <StreamingMessage
                    streamedAnswer={streamedAnswer}
                    isStreaming={true}
                    onCitationClick={onCitationClick}
                  />
                ) : (
                  <div className="flex gap-3">
                    <div className="w-6 h-6 shrink-0 bg-accent-ghost border border-accent/20 flex items-center justify-center text-accent mt-1">
                      <Bot className="w-3 h-3" />
                    </div>
                    <div className="flex-1 flex flex-col gap-2">
                      <span className="font-mono text-[10px] text-accent uppercase font-bold">
                        Assistant <span className="text-text-tertiary ml-2">PROCESSING</span>
                      </span>
                      <div className="bg-bg-surface border border-border-dim p-3">
                        <ThinkingIndicator step={currentStep} />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {isLoading && !isStreaming && (
          <div className="flex gap-3 animate-pulse">
            <div className="w-6 h-6 shrink-0 bg-accent-ghost border border-accent/20 flex items-center justify-center text-accent mt-1">
              <Loader2 className="w-3 h-3 animate-spin" />
            </div>
            <div className="flex-1 flex flex-col gap-1 justify-center">
              <span className="font-mono text-[10px] text-accent uppercase font-bold">Assistant</span>
              <div className="h-4 w-32 bg-bg-interactive border border-border-dim flex items-center px-2">
                <span className="text-[10px] font-mono text-text-tertiary">SEARCHING_TREE...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input Form */}
      <ChatInput onSubmit={onAsk} isLoading={isLoading || isStreaming} />
    </div>
  );
}
