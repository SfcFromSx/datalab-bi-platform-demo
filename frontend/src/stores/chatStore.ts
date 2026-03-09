import { create } from 'zustand';
import type { ChatMessage } from '../types';
import { wsClient } from '../services/websocket';

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  activeDatasourceId: string | null;
}

interface ChatActions {
  sendQuery: (query: string, notebookId: string, datasourceId?: string) => Promise<void>;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
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

    wsClient.send('agent_query', {
      query,
      datasource_id: dsId,
    });
  },

  addMessage: (message: ChatMessage) =>
    set((s) => ({ messages: [...s.messages, message] })),

  updateMessage: (id: string, updates: Partial<ChatMessage>) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),

  clearHistory: () => set({ messages: [] }),

  setDatasource: (id: string | null) => set({ activeDatasourceId: id }),
}));

wsClient.on('agent_progress', (message) => {
  const payload = message.payload as Record<string, any>;
  if (!payload.task_id) return;

  const store = useChatStore.getState();
  const existing = store.messages.find((m) => m.id === payload.task_id);

  if (existing) {
    store.updateMessage(payload.task_id, {
      content: payload.message || existing.content,
      data: payload.data,
      chart: payload.chart,
      sections: payload.sections,
    });
  } else {
    store.addMessage({
      id: payload.task_id,
      role: 'assistant',
      content: payload.message || 'Processing...',
      timestamp: Date.now(),
      data: payload.data,
      chart: payload.chart,
      sections: payload.sections,
    });
  }

  if (payload.status === 'error') {
    useChatStore.setState({ isLoading: false });
  }
});

wsClient.on('agent_complete', (message) => {
  const payload = message.payload as Record<string, any>;
  if (!payload.task_id) return;

  const store = useChatStore.getState();
  store.updateMessage(payload.task_id, {
    content: payload.message || 'Completed',
    cells_created: payload.cells_created,
    data: payload.data,
    chart: payload.chart,
    sections: payload.sections,
  });
  useChatStore.setState({ isLoading: false });
});
