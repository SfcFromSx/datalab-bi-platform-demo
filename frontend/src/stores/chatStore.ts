import { create } from 'zustand';
import type { ChatMessage, ChatMode, ChatStep, DesignAction } from '../types';
import { getApiBaseUrl, createCell, updateCell, deleteCellApi, moveCell, executeCell } from '../services/api';
import { useNotebookStore } from './notebookStore';

interface ChatState {
  messagesByMode: Record<ChatMode, ChatMessage[]>;
  isLoading: boolean;
  activeDatasourceId: string | null;
}

interface ChatActions {
  sendQuery: (query: string, notebookId?: string, datasourceId?: string) => Promise<void>;
  sendDesignQuery: (query: string, notebookId: string, datasourceId?: string) => Promise<void>;
  sendAgentTask: (query: string, notebookId?: string, datasourceId?: string) => Promise<void>;
  clearHistory: (mode: ChatMode) => void;
  setDatasource: (id: string | null) => void;
  getMessages: (mode: ChatMode) => ChatMessage[];
}

export const useChatStore = create<ChatState & ChatActions>((set, get) => ({
  messagesByMode: { chat: [], design: [], agent: [] },
  isLoading: false,
  activeDatasourceId: null,

  getMessages: (mode: ChatMode) => get().messagesByMode[mode],

  sendQuery: async (query: string, notebookId?: string, datasourceId?: string) => {
    const dsId = datasourceId ?? get().activeDatasourceId ?? undefined;
    const mode: ChatMode = 'chat';

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
      steps: [],
      status: 'done',
      mode,
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      steps: [],
      status: 'streaming',
      mode,
    };

    set((s) => ({
      messagesByMode: {
        ...s.messagesByMode,
        [mode]: [...s.messagesByMode[mode], userMsg, assistantMsg],
      },
      isLoading: true,
    }));

    try {
      const response = await fetch(`${getApiBaseUrl()}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          notebook_id: notebookId,
          datasource_id: dsId,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Chat request failed');
      }

      await _readSSEStream(response, assistantId, mode);
      _finalizeMessage(assistantId, 'done', mode);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Chat request failed';
      _appendStep(assistantId, { type: 'error', content: errMsg }, mode);
      _finalizeMessage(assistantId, 'error', mode);
    }

    set({ isLoading: false });
  },

  sendDesignQuery: async (query: string, notebookId: string, datasourceId?: string) => {
    const dsId = datasourceId ?? get().activeDatasourceId ?? undefined;
    const mode: ChatMode = 'design';

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
      steps: [],
      status: 'done',
      mode,
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      steps: [],
      status: 'streaming',
      mode,
    };

    set((s) => ({
      messagesByMode: {
        ...s.messagesByMode,
        [mode]: [...s.messagesByMode[mode], userMsg, assistantMsg],
      },
      isLoading: true,
    }));

    try {
      const response = await fetch(`${getApiBaseUrl()}/chat/design`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          notebook_id: notebookId,
          datasource_id: dsId,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Design request failed');
      }

      await _readSSEStream(response, assistantId, mode, notebookId);
      _finalizeMessage(assistantId, 'done', mode);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Design request failed';
      _appendStep(assistantId, { type: 'error', content: errMsg }, mode);
      _finalizeMessage(assistantId, 'error', mode);
    }

    set({ isLoading: false });
  },

  sendAgentTask: async (query: string, notebookId?: string, datasourceId?: string) => {
    const dsId = datasourceId ?? get().activeDatasourceId ?? undefined;
    const mode: ChatMode = 'agent';

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
      steps: [],
      status: 'done',
      mode,
    };

    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      steps: [],
      status: 'streaming',
      mode,
    };

    set((s) => ({
      messagesByMode: {
        ...s.messagesByMode,
        [mode]: [...s.messagesByMode[mode], userMsg, assistantMsg],
      },
      isLoading: true,
    }));

    try {
      const response = await fetch(`${getApiBaseUrl()}/agent-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          notebook_id: notebookId,
          datasource_id: dsId,
        }),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Agent task request failed');
      }

      await _readSSEStream(response, assistantId, mode, notebookId);
      _finalizeMessage(assistantId, 'done', mode);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Agent task request failed';
      _appendStep(assistantId, { type: 'error', content: errMsg }, mode);
      _finalizeMessage(assistantId, 'error', mode);
    }

    set({ isLoading: false });
  },

  clearHistory: (mode: ChatMode) =>
    set((s) => ({
      messagesByMode: { ...s.messagesByMode, [mode]: [] },
    })),

  setDatasource: (id) => set({ activeDatasourceId: id }),
}));

async function _readSSEStream(
  response: Response,
  messageId: string,
  mode: ChatMode,
  notebookId?: string,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No reader available');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      await _processSSE(raw, messageId, mode, notebookId);
      boundary = buffer.indexOf('\n\n');
    }

    if (done) {
      if (buffer.trim()) await _processSSE(buffer.trim(), messageId, mode, notebookId);
      break;
    }
  }
}

async function _processSSE(
  raw: string,
  messageId: string,
  mode: ChatMode,
  notebookId?: string,
) {
  let eventName = 'message';
  let data = '';

  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) eventName = line.slice(6).trim();
    else if (line.startsWith('data:')) data += line.slice(5).trim();
  }

  if (!data) return;

  try {
    const payload = JSON.parse(data);
    if (eventName === 'step') {
      await _handleStep(messageId, payload, mode, notebookId);
    } else if (eventName === 'done') {
      _finalizeMessage(messageId, 'done', mode);
    } else if (eventName === 'error') {
      _appendStep(messageId, { type: 'error', content: payload.message ?? 'Unknown error' }, mode);
      _finalizeMessage(messageId, 'error', mode);
    }
  } catch {
    // skip malformed events
  }
}

async function _handleStep(
  messageId: string,
  step: { type: string; content: unknown },
  mode: ChatMode,
  notebookId?: string,
) {
  const store = useChatStore.getState();
  const msg = store.messagesByMode[mode].find((m) => m.id === messageId);
  if (!msg) return;

  if (step.type === 'action' && mode === 'design' && notebookId) {
    const action = step.content as DesignAction;    const actionSteps: ChatStep[] = [...msg.steps, { type: 'action' as any, content: action, applied: false }];
    _updateMessage(messageId, { steps: actionSteps }, mode);

    try {
      await _applyDesignAction(action, notebookId);
      const currentMsg = useChatStore.getState().messagesByMode[mode].find((m) => m.id === messageId);
      if (currentMsg) {
        const updatedSteps = [...currentMsg.steps];
        const lastIdx = updatedSteps.length - 1;
        updatedSteps[lastIdx] = { ...updatedSteps[lastIdx], applied: true };
        _updateMessage(messageId, { steps: updatedSteps }, mode);
      }
      useNotebookStore.getState().loadNotebook(notebookId);
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Failed to apply action';
      const currentMsg = useChatStore.getState().messagesByMode[mode].find((m) => m.id === messageId);
      if (currentMsg) {
        const errorSteps: ChatStep[] = [...currentMsg.steps, { type: 'action_result' as any, content: `Error: ${errMsg}` }];
        _updateMessage(messageId, { steps: errorSteps }, mode);
      }
    }
    return;
  }

  const steps = [...msg.steps];

  // Clear ANY previous streaming step if we are starting a NEW step type
  // (unless it's an incremental update to the same type, like SQL)
  for (let i = steps.length - 1; i >= 0; i--) {
    if (steps[i].streaming) {
      if (steps[i].type !== step.type) {
        steps[i] = { ...steps[i], streaming: false };
      }
      break;
    }
  }

  if (step.type === 'sql') {
    const existing = steps.findIndex((s) => s.type === 'sql');
    if (existing >= 0) {
      steps[existing] = { type: 'sql', content: step.content as string, streaming: true };
    } else {
      steps.push({ type: 'sql', content: step.content as string, streaming: true });
    }
  } else if (step.type === 'thinking') {
    steps.push({ type: 'thinking', content: step.content as string, streaming: true });
  } else if (step.type === 'executing') {
    steps.push({ type: 'executing', content: step.content as string, streaming: true });
  } else {
    // Other types (data, answer, agent_progress, etc.)
    steps.push({
      type: step.type as ChatStep['type'],
      content: step.content as any,
      streaming: false,
    });
  }

  _updateMessage(messageId, { steps }, mode);
}

async function _applyDesignAction(action: DesignAction, notebookId: string) {
  switch (action.action) {
    case 'add_cell':
      await createCell(notebookId, action.cell_type ?? 'sql', action.source ?? '', action.position);
      break;
    case 'edit_cell':
      if (action.cell_id && action.source !== undefined) {
        await updateCell(action.cell_id, action.source);
      }
      break;
    case 'delete_cell':
      if (action.cell_id) {
        await deleteCellApi(action.cell_id);
      }
      break;
    case 'move_cell':
      if (action.cell_id && action.position !== undefined) {
        await moveCell(action.cell_id, action.position);
      }
      break;
    case 'execute_cell':
      if (action.cell_id) {
        await executeCell(action.cell_id);
      }
      break;
  }
}

function _appendStep(messageId: string, step: ChatStep, mode: ChatMode) {
  const store = useChatStore.getState();
  const msg = store.messagesByMode[mode].find((m) => m.id === messageId);
  if (!msg) return;
  _updateMessage(messageId, { steps: [...msg.steps, step] }, mode);
}

function _finalizeMessage(messageId: string, status: 'done' | 'error', mode: ChatMode) {
  const store = useChatStore.getState();
  const msg = store.messagesByMode[mode].find((m) => m.id === messageId);
  if (!msg) return;

  const steps = msg.steps.map((s) => ({ ...s, streaming: false }));
  const answerStep = steps.find((s) => s.type === 'answer' || s.type === 'summary');
  const content = typeof answerStep?.content === 'string' ? answerStep.content : msg.content;

  _updateMessage(messageId, { steps, status, content }, mode);
}

function _updateMessage(id: string, updates: Partial<ChatMessage>, mode: ChatMode) {
  useChatStore.setState((s) => ({
    messagesByMode: {
      ...s.messagesByMode,
      [mode]: s.messagesByMode[mode].map((m) => (m.id === id ? { ...m, ...updates } : m)),
    },
  }));
}
