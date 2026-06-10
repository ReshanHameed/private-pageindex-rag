import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Info, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import type { DocumentRecord, ChatRecord } from '@/lib/types';
import TraceTimeline from '@/components/trace/TraceTimeline';
import { toast } from 'sonner';

export default function TracePage() {
  const { docId, chatId } = useParams();
  
  // Find in store synchronously during render initialization
  const store = useAppStore.getState();
  const existingDoc = docId ? store.documents.find(d => d.id === docId) : undefined;
  const existingChat = chatId ? store.currentChats.find(c => c.id === chatId) : undefined;

  const [doc, setDoc] = useState<DocumentRecord | null>(existingDoc || null);
  const [chat, setChat] = useState<ChatRecord | null>(existingChat || null);
  const [isLoading, setIsLoading] = useState(!existingDoc || !existingChat);

  useEffect(() => {
    if (!docId || !chatId) return;

    // If both are already loaded from the store, do nothing
    if (existingDoc && existingChat) return;

    // Fallback to API if not in store (e.g. direct load, refresh)
    Promise.resolve().then(() => {
      setIsLoading(true);
    });
    Promise.all([
      existingDoc ? Promise.resolve(existingDoc) : api.fetchDocument(docId),
      existingChat ? Promise.resolve(existingChat) : api.fetchChatTrace(docId, chatId)
    ]).then(([d, chatTrace]) => {
      setDoc(d);
      setChat(chatTrace);
    }).catch(err => {
      console.error(err);
      toast.error('Failed to load trace data');
    }).finally(() => {
      setIsLoading(false);
    });
  }, [docId, chatId, existingDoc, existingChat]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[500px]">
        <Loader2 className="size-6 animate-spin text-accent" />
      </div>
    );
  }

  if (!doc || !chat) {
    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[500px] gap-4 font-mono">
        <div className="text-text-secondary">Failed to load trace data.</div>
        <Link to={`/documents/${docId}`} className="text-accent hover:underline">
          Return to Document
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full h-full overflow-y-auto animate-fade-in pb-12 pr-2">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-border-dim pb-4 select-none">
        <div className="flex items-center gap-3">
          <Link
            to={`/documents/${docId}`}
            className="p-1 border border-border-dim bg-bg-surface hover:bg-bg-interactive text-text-secondary hover:text-text-primary cursor-pointer transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
          >
            <ArrowLeft className="size-4" />
          </Link>
          <div className="flex flex-col">
            <h2 className="text-lg font-display font-medium text-text-primary leading-tight">
              Retrieval Trace Debugger
            </h2>
            <span className="font-mono text-[10px] text-text-tertiary uppercase">
              CHAT_ID: {chat.id} · DOCUMENT: {doc.filename}
            </span>
          </div>
        </div>
      </div>

      <div className="bg-bg-surface border border-border-dim p-4 flex flex-col gap-2">
        <div className="font-mono text-[10px] text-text-tertiary uppercase">Question</div>
        <div className="text-text-primary font-sans text-sm">{chat.question}</div>
      </div>

      {/* Trace timeline info box */}
      <div className="flex items-start gap-3 border border-info/20 bg-info/5 p-4 font-mono text-xs text-text-secondary leading-normal">
        <Info className="size-5 text-info mt-0.5 flex-none" />
        <div>
          <span className="text-info font-bold uppercase block mb-1">[TRACE_EXECUTION_METADATA]</span>
          This timeline captures the exact structural retrieval steps taken by the local LLM. Check which nodes were parsed, which pages were fetched into memory, and why they were chosen.
        </div>
      </div>

      {/* Timeline Steps */}
      <div className="mt-4">
        <TraceTimeline steps={chat.trace_steps} />
      </div>
    </div>
  );
}
