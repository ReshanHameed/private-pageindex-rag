/**
 * Zustand store for SSE streaming state during document Q&A.
 * Manages trace events, streaming tokens, and graph node activation.
 */
import { create } from 'zustand';

export interface TraceEvent {
  type: 'trace';
  step: string;
  detail: string;
  node_id?: string;
  node_ids?: string[];
  pages?: string;
}

export interface StreamState {
  /** Whether a streaming question is currently active */
  isStreaming: boolean;
  /** The current question being streamed */
  question: string;
  /** Accumulated trace events from the current stream */
  traceEvents: TraceEvent[];
  /** Accumulated answer tokens */
  streamedAnswer: string;
  /** Node IDs currently activated by the retrieval pipeline */
  activatedNodeIds: string[];
  /** Node IDs that have been "fetched" (pages retrieved) */
  fetchedNodeIds: string[];
  /** The latest trace step name for UI display */
  currentStep: string | null;
  /** Chat ID once the stream completes */
  completedChatId: string | null;
  /** Citations extracted from the final answer */
  citations: string[];
  /** Error message if streaming failed */
  error: string | null;

  // Actions
  startStream: (question: string) => void;
  addTraceEvent: (event: TraceEvent) => void;
  appendToken: (text: string) => void;
  completeStream: (chatId: string, answer: string, citations: string[]) => void;
  setError: (detail: string) => void;
  reset: () => void;
}

const initialState = {
  isStreaming: false,
  question: '',
  traceEvents: [] as TraceEvent[],
  streamedAnswer: '',
  activatedNodeIds: [] as string[],
  fetchedNodeIds: [] as string[],
  currentStep: null as string | null,
  completedChatId: null as string | null,
  citations: [] as string[],
  error: null as string | null,
};

export const useStreamStore = create<StreamState>((set) => ({
  ...initialState,

  startStream(question: string) {
    set({
      ...initialState,
      isStreaming: true,
      question,
    });
  },

  addTraceEvent(event: TraceEvent) {
    set((state) => {
      const updates: Partial<StreamState> = {
        traceEvents: [...state.traceEvents, event],
        currentStep: event.step,
      };

      // Track activated nodes from select_nodes step
      if (event.step === 'select_nodes' && event.node_ids) {
        updates.activatedNodeIds = event.node_ids;
      }

      // Track fetched nodes
      if (event.step === 'fetch_pages' && event.node_id) {
        updates.fetchedNodeIds = [...state.fetchedNodeIds, event.node_id];
      }

      return updates;
    });
  },

  appendToken(text: string) {
    set((state) => ({
      streamedAnswer: state.streamedAnswer + text,
      currentStep: 'generating',
    }));
  },

  completeStream(chatId: string, answer: string, citations: string[]) {
    set({
      isStreaming: false,
      completedChatId: chatId,
      streamedAnswer: answer,
      citations,
      currentStep: 'done',
    });
  },

  setError(detail: string) {
    set({
      isStreaming: false,
      error: detail,
      currentStep: 'error',
    });
  },

  reset() {
    set(initialState);
  },
}));
