import type { DocumentRecord, OllamaStatusResponse, OllamaModelsResponse } from './types';

export const api = {
  async fetchDocuments(): Promise<DocumentRecord[]> {
    const res = await fetch('/api/documents');
    if (!res.ok) {
      throw new Error(`Failed to fetch documents: ${res.statusText}`);
    }
    return res.json();
  },

  async uploadDocument(file: File, model?: string): Promise<DocumentRecord> {
    const formData = new FormData();
    formData.append('file', file);
    if (model) {
      formData.append('model', model);
    }

    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${res.statusText}`);
    }
    return res.json();
  },

  async deleteDocument(docId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`/api/documents/${docId}/delete`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error(`Failed to delete document: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchDocumentStatus(docId: string): Promise<DocumentRecord> {
    const res = await fetch(`/api/documents/${docId}/status`);
    if (!res.ok) {
      throw new Error(`Failed to fetch status: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchOllamaStatus(): Promise<OllamaStatusResponse> {
    const res = await fetch('/api/ollama-status');
    if (!res.ok) {
      throw new Error(`Failed to fetch Ollama status: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchOllamaModels(): Promise<OllamaModelsResponse> {
    const res = await fetch('/api/ollama-models');
    if (!res.ok) {
      throw new Error(`Failed to fetch Ollama models: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchDocument(docId: string): Promise<DocumentRecord> {
    const res = await fetch(`/api/documents/${docId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch document: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchDocumentTree(docId: string): Promise<import('./types').TreeJSON> {
    const res = await fetch(`/api/documents/${docId}/tree`);
    if (!res.ok) {
      throw new Error(`Failed to fetch document tree: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchDocumentSessions(docId: string): Promise<import('./types').ChatSession[]> {
    const res = await fetch(`/api/documents/${docId}/sessions`);
    if (!res.ok) {
      throw new Error(`Failed to fetch document sessions: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchSessionChats(docId: string, sessionId: string): Promise<import('./types').ChatRecord[]> {
    const res = await fetch(`/api/documents/${docId}/sessions/${sessionId}/chats`);
    if (!res.ok) {
      throw new Error(`Failed to fetch session chats: ${res.statusText}`);
    }
    return res.json();
  },

  async fetchChatTrace(docId: string, chatId: string): Promise<import('./types').ChatRecord> {
    const res = await fetch(`/api/documents/${docId}/chats/${chatId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch chat trace: ${res.statusText}`);
    }
    return res.json();
  },

  async deleteSession(docId: string, sessionId: string): Promise<void> {
    const res = await fetch(`/api/documents/${docId}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      throw new Error(`Failed to delete session: ${res.statusText}`);
    }
  },
};
