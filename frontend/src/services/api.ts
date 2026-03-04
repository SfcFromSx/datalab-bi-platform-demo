import axios from 'axios';
import type {
  AgentQueryResponse,
  Cell,
  CellType,
  DataSource,
  Folder,
  Notebook,
  NotebookListItem,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export const listNotebooks = () =>
  api.get<NotebookListItem[]>('/notebooks').then((r) => r.data);

export const createNotebook = (title = 'Untitled Notebook', description = '') =>
  api.post<Notebook>('/notebooks', { title, description }).then((r) => r.data);

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
  onChunk: (chunk: string) => void
) => {
  const response = await fetch(`http://localhost:8000/api/cells/${cellId}/edit-with-ai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    throw new Error('AI Edit request failed');
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No reader available');

  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    onChunk(chunk);
  }
};

export const moveCell = (cellId: string, position: number) =>
  api.put<Cell>(`/cells/${cellId}/move`, { position }).then((r) => r.data);

export const executeCell = (cellId: string, source?: string) =>
  api.post<{ cell_id: string; status: string; output: Record<string, unknown> }>(
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

export default api;
