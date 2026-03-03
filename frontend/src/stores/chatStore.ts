import { create } from 'zustand';
import type { ChatMessage } from '../types';
import { agentQuery } from '../services/api';

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  activeDatasourceId: string | null;
}

interface ChatActions {
  sendQuery: (query: string, notebookId: string, datasourceId?: string) => Promise<void>;
  addMessage: (message: ChatMessage) => void;
  clearHistory: () => void;
  setDatasource: (id: string | null) => void;
}

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  messages: [],
  isLoading: false,
  activeDatasourceId: null,

  sendQuery: async (query: string, notebookId: string, datasourceId?: string) => {
    const { activeDatasourceId } = get();
    const dsId = datasourceId ?? activeDatasourceId ?? undefined;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
    };
    set((s) => ({ messages: [...s.messages, userMessage], isLoading: true }));

    try {
      const response = await agentQuery(query, notebookId, dsId);
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.message,
        timestamp: Date.now(),
        cells_created: response.cells_created,
      };
      set((s) => ({
        messages: [...s.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (e) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: e instanceof Error ? e.message : 'Query failed',
        timestamp: Date.now(),
      };
      set((s) => ({
        messages: [...s.messages, errorMessage],
        isLoading: false,
      }));
    }
  },

  addMessage: (message: ChatMessage) =>
    set((s) => ({ messages: [...s.messages, message] })),

  clearHistory: () => set({ messages: [] }),

  setDatasource: (id: string | null) => set({ activeDatasourceId: id }),
}));
