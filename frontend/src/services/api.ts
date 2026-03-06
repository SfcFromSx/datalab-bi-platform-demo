import axios, { AxiosHeaders } from 'axios';
import type {
  AuditEvent,
  AgentQueryResponse,
  Cell,
  CellAgentRuntimeInfo,
  CellExecuteResult,
  CellType,
  DataSource,
  EnterpriseContext,
  Folder,
  Notebook,
  NotebookListItem,
} from '../types';

const WORKSPACE_STORAGE_KEY = 'datalab.workspaceKey';
const USER_EMAIL_STORAGE_KEY = 'datalab.userEmail';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

function readStorageValue(key: string) {
  if (typeof window === 'undefined') {
    return null;
  }
  return window.localStorage.getItem(key);
}

export function getStoredWorkspaceKey() {
  return readStorageValue(WORKSPACE_STORAGE_KEY);
}

export function setStoredWorkspaceKey(workspaceKey: string | null) {
  if (typeof window === 'undefined') {
    return;
  }
  if (workspaceKey) {
    window.localStorage.setItem(WORKSPACE_STORAGE_KEY, workspaceKey);
  } else {
    window.localStorage.removeItem(WORKSPACE_STORAGE_KEY);
  }
}

export function getStoredUserEmail() {
  return readStorageValue(USER_EMAIL_STORAGE_KEY);
}

export function setStoredUserEmail(userEmail: string | null) {
  if (typeof window === 'undefined') {
    return;
  }
  if (userEmail) {
    window.localStorage.setItem(USER_EMAIL_STORAGE_KEY, userEmail);
  } else {
    window.localStorage.removeItem(USER_EMAIL_STORAGE_KEY);
  }
}

export function getEnterpriseHeaders() {
  const workspaceKey = getStoredWorkspaceKey();
  const userEmail = getStoredUserEmail();

  return {
    ...(workspaceKey ? { 'X-DataLab-Workspace': workspaceKey } : {}),
    ...(userEmail ? { 'X-DataLab-User-Email': userEmail } : {}),
  };
}

export function getApiBaseUrl() {
  return typeof api.defaults.baseURL === 'string' ? api.defaults.baseURL : '/api';
}

api.interceptors.request.use((config) => {
  const headers = AxiosHeaders.from(config.headers);
  Object.entries(getEnterpriseHeaders()).forEach(([key, value]) => {
    if (value) {
      headers.set(key, value);
    }
  });
  config.headers = headers;
  return config;
});

export const listNotebooks = () =>
  api.get<NotebookListItem[]>('/notebooks').then((r) => r.data);

export const createNotebook = (
  title = 'Untitled Notebook',
  description = '',
  folderId?: string
) =>
  api.post<Notebook>('/notebooks', {
    title,
    description,
    folder_id: folderId,
  }).then((r) => r.data);

export const getNotebook = (id: string) =>
  api.get<Notebook>(`/notebooks/${id}`).then((r) => r.data);

export const updateNotebook = (id: string, data: { title?: string; description?: string }) =>
  api.put<Notebook>(`/notebooks/${id}`, data).then((r) => r.data);

export const deleteNotebook = (id: string) => api.delete(`/notebooks/${id}`);

export const moveNotebookToFolder = (id: string, folderId: string | null) =>
  api.put<Notebook>(`/notebooks/${id}`, { folder_id: folderId ?? '' }).then((r) => r.data);

// --- Folder API ---
export const listFolders = () =>
  api.get<Folder[]>('/folders').then((r) => r.data);

export const createFolder = (name = 'New Folder') =>
  api.post<Folder>('/folders', { name }).then((r) => r.data);

export const updateFolder = (id: string, data: { name?: string; position?: number }) =>
  api.put<Folder>(`/folders/${id}`, data).then((r) => r.data);

export const deleteFolder = (id: string) => api.delete(`/folders/${id}`);

export const createCell = (notebookId: string, cellType: CellType, source = '', position?: number) =>
  api.post<Cell>(`/notebooks/${notebookId}/cells`, {
    cell_type: cellType, source, position,
  }).then((r) => r.data);

export const updateCell = (cellId: string, source: string) =>
  api.put<Cell>(`/cells/${cellId}`, { source }).then((r) => r.data);

export const deleteCellApi = (cellId: string) => api.delete(`/cells/${cellId}`);

export const editCellWithAIStream = async (
  cellId: string,
  prompt: string,
  handlers: {
    onProgress?: (payload: {
      stage: string;
      message: string;
      progress: number;
      details?: CellAgentRuntimeInfo;
    }) => void;
    onChunk?: (payload: { content: string }) => void;
    onDone?: (payload: {
      content: string;
      progress: number;
      message: string;
      details?: CellAgentRuntimeInfo;
    }) => void;
    onError?: (payload: {
      message: string;
      progress?: number;
      details?: CellAgentRuntimeInfo;
    }) => void;
  }
) => {
  const response = await fetch(`${getApiBaseUrl()}/cells/${cellId}/edit-with-ai`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getEnterpriseHeaders(),
    },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'AI Edit request failed');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No reader available');

  const decoder = new TextDecoder();
  let buffer = '';

  const emitEvent = (rawEvent: string) => {
    const lines = rawEvent.split('\n');
    let eventName = 'message';
    let data = '';

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        data += line.slice(5).trim();
      }
    }

    if (!data) {
      return;
    }

    const payload = JSON.parse(data);
    if (eventName === 'progress') {
      handlers.onProgress?.(payload);
    } else if (eventName === 'chunk') {
      handlers.onChunk?.(payload);
    } else if (eventName === 'done') {
      handlers.onDone?.(payload);
    } else if (eventName === 'error') {
      handlers.onError?.(payload);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });

    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      emitEvent(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');
    }

    if (done) {
      if (buffer.trim()) {
        emitEvent(buffer.trim());
      }
      break;
    }
  }
};

export const moveCell = (cellId: string, position: number) =>
  api.put<Cell>(`/cells/${cellId}/move`, { position }).then((r) => r.data);

export const executeCell = (cellId: string, source?: string) =>
  api.post<CellExecuteResult>(
    `/cells/${cellId}/execute`, source ? { source } : {}
  ).then((r) => r.data);

export const agentQuery = (query: string, notebookId: string, datasourceId?: string) =>
  api.post<AgentQueryResponse>('/agents/query', {
    query, notebook_id: notebookId, datasource_id: datasourceId,
  }).then((r) => r.data);

export const listDataSources = () =>
  api.get<DataSource[]>('/datasources').then((r) => r.data);

export const uploadCSV = (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post<DataSource>('/datasources/upload-csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data);
};

export const getDataSourceSchema = (id: string) =>
  api.get(`/datasources/${id}/schema`).then((r) => r.data);

export const searchKnowledge = (query: string, datasourceId?: string) =>
  api.get('/knowledge/search', { params: { query, datasource_id: datasourceId } })
    .then((r) => r.data);

export const healthCheck = () => api.get('/health').then((r) => r.data);

export const getEnterpriseContext = () =>
  api.get<EnterpriseContext>('/enterprise/context').then((r) => r.data);

export const listAuditEvents = (limit = 50) =>
  api.get<AuditEvent[]>('/enterprise/audit-events', { params: { limit } }).then((r) => r.data);

export default api;
