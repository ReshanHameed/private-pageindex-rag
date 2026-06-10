import { create } from 'zustand';
import type { DocumentRecord, ChatRecord, ChatSession } from './types';
import { api } from './api';
import { toast } from 'sonner';

interface AppState {
  documents: DocumentRecord[];
  loading: boolean;
  error: string | null;
  ollamaStatus: 'connected' | 'offline' | 'checking' | null;
  ollamaModels: string[];
  selectedModel: string;
  currentSessions: ChatSession[];
  currentChats: ChatRecord[];
  activeSessionId: string | null;

  fetchDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  fetchOllamaStatusAndModels: () => Promise<void>;
  setSelectedModel: (model: string) => void;
  setCurrentChats: (chats: ChatRecord[]) => void;
  setActiveSessionId: (sessionId: string | null) => void;
  fetchSessionsAndChats: (docId: string, sessionId?: string | null) => Promise<void>;
  fetchCurrentChats: (docId: string, sessionId: string) => Promise<void>;
  deleteSession: (docId: string, sessionId: string) => Promise<void>;
  initialize: () => Promise<void>;
  cleanup: () => void;
}

let pollIntervalId: ReturnType<typeof setInterval> | null = null;

const startPolling = (get: () => AppState, set: (state: Partial<AppState>) => void) => {
  if (pollIntervalId) return;

  pollIntervalId = setInterval(async () => {
    const docs = get().documents;
    const processingDocs = docs.filter((d) => d.status === 'processing');

    if (processingDocs.length === 0) {
      if (pollIntervalId) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
      }
      return;
    }

    try {
      const updatedDocs = await Promise.all(
        docs.map(async (doc) => {
          if (doc.status !== 'processing') return doc;
          try {
            const latest = await api.fetchDocumentStatus(doc.id);
            if (latest.status === 'completed') {
              toast.success(`Index Complete: ${latest.filename}`, {
                description: `${latest.page_count} pages indexed in ${latest.elapsed_seconds}s.`,
              });
            } else if (latest.status === 'failed') {
              toast.error(`Index Failed: ${latest.filename}`, {
                description: latest.error || 'Unknown error occurred.',
              });
            }
            return latest;
          } catch (err) {
            console.error(`Error polling document ${doc.id}:`, err);
            return doc;
          }
        })
      );

      const hasChanges = updatedDocs.some((d, idx) => {
        const original = docs[idx];
        return (
          d.status !== original.status ||
          d.progress_percent !== original.progress_percent ||
          d.progress_stage !== original.progress_stage ||
          d.elapsed_seconds !== original.elapsed_seconds
        );
      });

      if (hasChanges) {
        set({ documents: updatedDocs });
      }
    } catch (err) {
      console.error('Error in polling loop:', err);
    }
  }, 2000);
};

const initialModel = localStorage.getItem('selected_model') || 'gemma4:e4b';

export const useAppStore = create<AppState>((set, get) => ({
  documents: [],
  loading: false,
  error: null,
  ollamaStatus: null,
  ollamaModels: [initialModel],
  selectedModel: initialModel,
  currentSessions: [],
  currentChats: [],
  activeSessionId: null,

  setCurrentChats(chats) {
    set({ currentChats: chats });
  },

  setActiveSessionId(sessionId) {
    set({ activeSessionId: sessionId });
  },

  async fetchSessionsAndChats(docId, sessionId) {
    try {
      const sessions = await api.fetchDocumentSessions(docId);
      set({ currentSessions: sessions });
      
      let targetSessionId = sessionId;
      const isValidSession = sessionId && sessions.some((s) => s.id === sessionId);
      if (!isValidSession) {
          targetSessionId = sessions.length > 0 ? sessions[0].id : null;
      }
      
      set({ activeSessionId: targetSessionId });
      
      if (targetSessionId) {
        await get().fetchCurrentChats(docId, targetSessionId);
      } else {
        set({ currentChats: [] });
      }
    } catch (err) {
      console.error('Failed to fetch sessions and chats:', err);
    }
  },

  async fetchCurrentChats(docId, sessionId) {
    try {
      const chats = await api.fetchSessionChats(docId, sessionId);
      set({ currentChats: chats });
    } catch (err) {
      console.error('Failed to fetch chats:', err);
    }
  },

  async deleteSession(docId, sessionId) {
    try {
      await api.deleteSession(docId, sessionId);
      const { currentSessions, activeSessionId } = get();
      const updatedSessions = currentSessions.filter(s => s.id !== sessionId);
      set({ currentSessions: updatedSessions });
      
      if (activeSessionId === sessionId) {
        const nextSessionId = updatedSessions.length > 0 ? updatedSessions[0].id : null;
        set({ activeSessionId: nextSessionId });
        if (nextSessionId) {
          await get().fetchCurrentChats(docId, nextSessionId);
        } else {
          set({ currentChats: [] });
        }
      }
      toast.success('Chat session deleted');
    } catch (err) {
      console.error('Failed to delete session:', err);
      toast.error('Failed to delete session');
    }
  },

  async fetchDocuments() {
    set({ loading: true, error: null });
    try {
      const docs = await api.fetchDocuments();
      set({ documents: docs, loading: false });
      
      // Start polling if there are any processing documents
      if (docs.some((d) => d.status === 'processing')) {
        startPolling(get, set);
      }
    } catch (err) {
      set({ error: (err as Error).message, loading: false });
    }
  },

  async uploadDocument(file: File) {
    // Optimistic addition of the processing card
    const tempId = `temp-${Date.now()}`;
    const optimisticDoc: DocumentRecord = {
      id: tempId,
      filename: file.name,
      status: 'processing',
      page_count: null,
      error: null,
      created_at: new Date().toISOString(),
      progress_percent: 0,
      progress_stage: 'uploading',
      elapsed_seconds: 0,
    };

    set((state) => ({
      documents: [optimisticDoc, ...state.documents],
    }));

    try {
      const model = get().selectedModel;
      const actualDoc = await api.uploadDocument(file, model);
      
      // Replace optimistic document with actual
      set((state) => ({
        documents: state.documents.map((d) => (d.id === tempId ? actualDoc : d)),
      }));

      toast.info(`Ingestion started for: ${file.name}`);
      startPolling(get, set);
    } catch (err) {
      // Remove the optimistic document and show error
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== tempId),
      }));
      toast.error(`Upload failed: ${file.name}`, {
        description: (err as Error).message,
      });
    }
  },

  async deleteDocument(docId: string) {
    const originalDocs = get().documents;
    const targetDoc = originalDocs.find((d) => d.id === docId);

    // Optimistic remove
    set((state) => ({
      documents: state.documents.filter((d) => d.id !== docId),
    }));

    try {
      await api.deleteDocument(docId);
      toast.success(`Purged document: ${targetDoc?.filename || docId}`);
    } catch (err) {
      // Rollback
      set({ documents: originalDocs });
      toast.error(`Deletion failed: ${targetDoc?.filename || docId}`, {
        description: (err as Error).message,
      });
    }
  },

  async fetchOllamaStatusAndModels() {
    set({ ollamaStatus: 'checking' });
    try {
      const data = await api.fetchOllamaModels();
      const isConnected = data.status === 'connected' || data.status === 'ok';
      
      const newModels = data.models && data.models.length > 0 ? data.models : [initialModel];
      
      // If persisted model is not in available models, default to the first one available
      let modelToSelect = get().selectedModel;
      if (data.models && data.models.length > 0 && !data.models.includes(modelToSelect)) {
        modelToSelect = data.models.includes(data.default_model) ? data.default_model : data.models[0];
      }

      set({
        ollamaStatus: isConnected ? 'connected' : 'offline',
        ollamaModels: newModels,
        selectedModel: modelToSelect,
      });
    } catch {
      set({ ollamaStatus: 'offline', ollamaModels: [initialModel] });
    }
  },

  setSelectedModel(model: string) {
    localStorage.setItem('selected_model', model);
    set({ selectedModel: model });
  },

  async initialize() {
    await Promise.all([
      get().fetchOllamaStatusAndModels(),
      get().fetchDocuments(),
    ]);
  },

  cleanup() {
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
  },
}));
