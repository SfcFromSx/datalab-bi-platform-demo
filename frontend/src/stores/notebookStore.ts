import { create } from 'zustand';
import type { Cell, CellAIState, CellType, Folder, Notebook, NotebookListItem } from '../types';
import { wsClient } from '../services/websocket';
import {
  listNotebooks,
  createNotebook as createNotebookApi,
  deleteNotebook as deleteNotebookApi,
  updateNotebook as updateNotebookApi,
  moveNotebookToFolder as moveNotebookToFolderApi,
  getNotebook,
  listFolders,
  createFolder as createFolderApi,
  updateFolder as updateFolderApi,
  deleteFolder as deleteFolderApi,
  createCell as createCellApi,
  updateCell as updateCellApi,
  deleteCellApi,
  moveCell as moveCellApi,
  executeCell as executeCellApi,
} from '../services/api';

interface NotebookState {
  notebooks: NotebookListItem[];
  folders: Folder[];
  activeNotebook: Notebook | null;
  cells: Cell[];
  aiEditStateByCellId: Record<string, CellAIState>;
  loading: boolean;
  error: string | null;
}

interface NotebookActions {
  fetchNotebooks: () => Promise<void>;
  createNotebook: (title?: string, description?: string, folderId?: string) => Promise<Notebook | null>;
  deleteNotebook: (id: string) => Promise<void>;
  renameNotebook: (id: string, title: string) => Promise<void>;
  moveToFolder: (notebookId: string, folderId: string | null) => Promise<void>;
  loadNotebook: (id: string) => Promise<void>;
  // Folder actions
  fetchFolders: () => Promise<void>;
  createFolder: (name?: string) => Promise<Folder | null>;
  renameFolder: (id: string, name: string) => Promise<void>;
  removeFolder: (id: string) => Promise<void>;
  addCell: (cell_type: CellType, source?: string, position?: number) => Promise<Cell | null>;
  updateCellSource: (cellId: string, source: string) => Promise<void>;
  deleteCell: (cellId: string) => Promise<void>;
  moveCell: (cellId: string, position: number) => Promise<void>;
  executeCell: (cellId: string, source?: string) => Promise<void>;
  editCellWithAI: (cellId: string, prompt: string) => Promise<void>;
  clearCellAIState: (cellId: string) => void;
  setCells: (cells: Cell[]) => void;
}

const _debouncedSaveTimers: Record<string, ReturnType<typeof setTimeout>> = {};
const DEBOUNCE_MS = 400;

export const useNotebookStore = create<NotebookState & NotebookActions>((set, get) => ({
  notebooks: [],
  folders: [],
  activeNotebook: null,
  cells: [],
  aiEditStateByCellId: {},
  loading: false,
  error: null,

  fetchNotebooks: async () => {
    set({ loading: true, error: null });
    try {
      const notebooks = await listNotebooks();
      set({ notebooks, loading: false });
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to fetch notebooks',
      });
    }
  },

  createNotebook: async (title = 'Untitled Notebook', description = '', folderId?: string) => {
    set({ loading: true, error: null });
    try {
      const notebook = await createNotebookApi(title, description, folderId);
      const listItem: NotebookListItem = {
        id: notebook.id,
        title: notebook.title,
        description: notebook.description,
        folder_id: notebook.folder_id ?? null,
        created_at: notebook.created_at,
        updated_at: notebook.updated_at,
        cell_count: notebook.cells?.length ?? 0,
      };
      set((s) => ({
        notebooks: [listItem, ...s.notebooks],
        activeNotebook: notebook,
        cells: notebook.cells ?? [],
        aiEditStateByCellId: {},
        loading: false,
      }));
      return notebook;
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to create notebook',
      });
      return null;
    }
  },

  deleteNotebook: async (id: string) => {
    set({ loading: true, error: null });
    try {
      await deleteNotebookApi(id);
      const { activeNotebook } = get();
      set((s) => ({
        notebooks: s.notebooks.filter((nb) => nb.id !== id),
        activeNotebook: activeNotebook?.id === id ? null : s.activeNotebook,
        cells: activeNotebook?.id === id ? [] : s.cells,
        aiEditStateByCellId: activeNotebook?.id === id ? {} : s.aiEditStateByCellId,
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to delete notebook',
      });
    }
  },

  renameNotebook: async (id: string, title: string) => {
    set({ loading: true, error: null });
    try {
      const updated = await updateNotebookApi(id, { title });
      set((s) => ({
        notebooks: s.notebooks.map((nb) =>
          nb.id === id ? { ...nb, title: updated.title } : nb
        ),
        activeNotebook:
          s.activeNotebook?.id === id
            ? { ...s.activeNotebook, title: updated.title }
            : s.activeNotebook,
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to rename notebook',
      });
    }
  },

  moveToFolder: async (notebookId: string, folderId: string | null) => {
    set({ loading: true, error: null });
    try {
      await moveNotebookToFolderApi(notebookId, folderId);
      set((s) => ({
        notebooks: s.notebooks.map((nb) =>
          nb.id === notebookId ? { ...nb, folder_id: folderId } : nb
        ),
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to move notebook',
      });
    }
  },

  loadNotebook: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const notebook = await getNotebook(id);
      set({
        activeNotebook: notebook,
        cells: notebook.cells ?? [],
        aiEditStateByCellId: {},
        loading: false,
      });
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to load notebook',
      });
    }
  },

  addCell: async (cell_type: CellType, source = '', position?: number) => {
    const { activeNotebook } = get();
    if (!activeNotebook) return null;
    set({ loading: true, error: null });
    try {
      const cell = await createCellApi(activeNotebook.id, cell_type, source, position);
      set((s) => ({
        cells: [...s.cells, cell].sort((a, b) => a.position - b.position),
        loading: false,
      }));
      return cell;
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to add cell',
      });
      return null;
    }
  },

  updateCellSource: async (cellId: string, source: string) => {
    set((s) => ({
      cells: s.cells.map((c) => (c.id === cellId ? { ...c, source } : c)),
    }));

    if (_debouncedSaveTimers[cellId]) {
      clearTimeout(_debouncedSaveTimers[cellId]);
    }
    _debouncedSaveTimers[cellId] = setTimeout(async () => {
      delete _debouncedSaveTimers[cellId];
      try {
        const cell = await updateCellApi(cellId, source);
        set((s) => ({
          cells: s.cells.map((c) => (c.id === cellId ? cell : c)),
        }));
      } catch (e) {
        set({
          error: e instanceof Error ? e.message : 'Failed to update cell',
        });
      }
    }, DEBOUNCE_MS);
  },

  editCellWithAI: async (cellId: string, prompt: string) => {
    const currentState = get().aiEditStateByCellId[cellId];
    if (currentState?.status === 'generating') {
      throw new Error('An AI edit is already in progress for this cell.');
    }

    set({ error: null });
    const originalSource = get().cells.find((cell) => cell.id === cellId)?.source ?? '';
    try {
      set((s) => ({
        aiEditStateByCellId: {
          ...s.aiEditStateByCellId,
          [cellId]: {
            status: 'generating',
            stage: 'context',
            message: 'Starting AI rewrite',
            progress: 0.02,
            draft: '',
            prompt,
            details: null,
            error: null,
          },
        },
      }));

      await import('../services/api').then((api) => api.editCellWithAIStream(cellId, prompt, {
        onProgress: (payload) => {
          set((s) => ({
            aiEditStateByCellId: {
              ...s.aiEditStateByCellId,
              [cellId]: {
                ...(s.aiEditStateByCellId[cellId] ?? {
                  status: 'generating',
                  draft: '',
                  error: null,
                }),
                status: 'generating',
                stage: payload.stage,
                message: payload.message,
                progress: payload.progress,
                prompt: payload.prompt ?? s.aiEditStateByCellId[cellId]?.prompt ?? prompt,
                details: payload.details ?? s.aiEditStateByCellId[cellId]?.details ?? null,
              },
            },
          }));
        },
        onChunk: ({ content }) => {
          set((s) => ({
            aiEditStateByCellId: {
              ...s.aiEditStateByCellId,
              [cellId]: {
                ...(s.aiEditStateByCellId[cellId] ?? {
                  status: 'generating',
                  stage: 'generate',
                  message: 'Streaming draft',
                  progress: 0.35,
                  draft: '',
                  error: null,
                }),
                status: 'generating',
                draft: (s.aiEditStateByCellId[cellId]?.draft ?? '') + content,
              },
            },
          }));
        },
        onDone: async ({ content, progress, message, details }) => {
          const savedCell = await updateCellApi(cellId, content);
          set((s) => ({
            cells: s.cells.map((cell) => (cell.id === cellId ? savedCell : cell)),
            aiEditStateByCellId: {
              ...s.aiEditStateByCellId,
              [cellId]: {
                status: 'completed',
                stage: 'done',
                message,
                progress,
                draft: content,
                details,
                error: null,
              },
            },
          }));
        },
        onError: ({ message, details }) => {
          set((s) => ({
            aiEditStateByCellId: {
              ...s.aiEditStateByCellId,
              [cellId]: {
                ...(s.aiEditStateByCellId[cellId] ?? {
                  stage: 'error',
                  progress: 1,
                  draft: originalSource,
                }),
                status: 'error',
                stage: 'error',
                message,
                progress: 1,
                details: details ?? s.aiEditStateByCellId[cellId]?.details ?? null,
                error: message,
              },
            },
            error: message,
          }));
        },
      }));
    } catch (e) {
      set((s) => ({
        aiEditStateByCellId: {
          ...s.aiEditStateByCellId,
          [cellId]: {
            status: 'error',
            stage: 'error',
            message: e instanceof Error ? e.message : 'AI Edit failed',
            progress: 1,
            draft: originalSource,
            error: e instanceof Error ? e.message : 'AI Edit failed',
          },
        },
        error: e instanceof Error ? e.message : 'AI Edit failed',
      }));
    }
  },

  deleteCell: async (cellId: string) => {
    set({ loading: true, error: null });
    try {
      await deleteCellApi(cellId);
      set((s) => ({
        cells: s.cells.filter((c) => c.id !== cellId),
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to delete cell',
      });
    }
  },

  moveCell: async (cellId: string, position: number) => {
    set({ loading: true, error: null });
    try {
      const cell = await moveCellApi(cellId, position);
      set((s) => ({
        cells: s.cells.map((c) => (c.id === cellId ? cell : c)).sort((a, b) => a.position - b.position),
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to move cell',
      });
    }
  },

  executeCell: async (cellId: string, source?: string) => {
    set({ loading: true, error: null });
    try {
      const result = await executeCellApi(cellId, source);
      set((s) => ({
        cells: s.cells.map((c) => {
          const executedCell = result.executed_cells.find((item) => item.cell_id === c.id);
          if (executedCell) {
            return { ...c, output: executedCell.output };
          }
          if (c.id === cellId) {
            return { ...c, output: result.output };
          }
          return c;
        }),
        loading: false,
      }));
    } catch (e) {
      set((s) => ({
        cells: s.cells.map((c) =>
          c.id === cellId
            ? { ...c, output: { status: 'error', error: e instanceof Error ? e.message : 'Execution failed' } }
            : c
        ),
        loading: false,
      }));
    }
  },

  clearCellAIState: (cellId: string) =>
    set((s) => {
      const next = { ...s.aiEditStateByCellId };
      delete next[cellId];
      return { aiEditStateByCellId: next };
    }),

  setCells: (cells: Cell[]) => set({ cells }),

  fetchFolders: async () => {
    try {
      const folders = await listFolders();
      set({ folders });
    } catch (e) {
      console.error('Failed to fetch folders:', e);
    }
  },

  createFolder: async (name = 'New Folder') => {
    try {
      const folder = await createFolderApi(name);
      set((s) => ({ folders: [...s.folders, folder] }));
      return folder;
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to create folder' });
      return null;
    }
  },

  renameFolder: async (id: string, name: string) => {
    try {
      const updated = await updateFolderApi(id, { name });
      set((s) => ({
        folders: s.folders.map((f) => (f.id === id ? { ...f, name: updated.name } : f)),
      }));
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to rename folder' });
    }
  },

  removeFolder: async (id: string) => {
    try {
      await deleteFolderApi(id);
      set((s) => ({
        folders: s.folders.filter((f) => f.id !== id),
        notebooks: s.notebooks.map((nb) =>
          nb.folder_id === id ? { ...nb, folder_id: null } : nb
        ),
      }));
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to delete folder' });
    }
  },
}));

wsClient.on('cell_update', (message) => {
  const payload = message.payload as Record<string, any>;
  if (!payload.cell_id) return;
  const store = useNotebookStore.getState();
  store.setCells(
    store.cells.map((c) => {
      if (c.id === payload.cell_id) {
        return {
          ...c,
          output: payload.output || { status: payload.status, error: c.output?.error }
        };
      }
      return c;
    })
  );
});

