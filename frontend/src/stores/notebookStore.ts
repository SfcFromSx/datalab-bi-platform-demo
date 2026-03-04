import { create } from 'zustand';
import type { Cell, CellType, Folder, Notebook, NotebookListItem } from '../types';
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
  setCells: (cells: Cell[]) => void;
}

export const useNotebookStore = create<NotebookState & NotebookActions>((set, get) => ({
  notebooks: [],
  folders: [],
  activeNotebook: null,
  cells: [],
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
      const notebook = await createNotebookApi(title, description);
      // If folderId provided, move notebook to folder immediately
      if (folderId) {
        await moveNotebookToFolderApi(notebook.id, folderId);
        notebook.folder_id = folderId;
      }
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
    set({ loading: true, error: null });
    try {
      const cell = await updateCellApi(cellId, source);
      set((s) => ({
        cells: s.cells.map((c) => (c.id === cellId ? cell : c)),
        loading: false,
      }));
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : 'Failed to update cell',
      });
    }
  },

  editCellWithAI: async (cellId: string, prompt: string) => {
    set({ error: null });
    try {
      // Create a temporary backup of old source in case of failure? (Ignoring for now)
      set((s) => ({
        cells: s.cells.map((c) => (c.id === cellId ? { ...c, source: '' } : c)),
      }));

      await import('../services/api').then((api) => api.editCellWithAIStream(
        cellId,
        prompt,
        (chunk) => {
          set((s) => ({
            cells: s.cells.map((c) =>
              c.id === cellId ? { ...c, source: c.source + chunk } : c
            ),
          }));
        }
      ));

      // Save full result at the end
      const finalCell = get().cells.find(c => c.id === cellId);
      if (finalCell) {
        await updateCellApi(cellId, finalCell.source);
      }
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'AI Edit failed' });
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
        cells: s.cells.map((c) =>
          c.id === cellId ? { ...c, output: result.output as unknown as Cell['output'] } : c
        ),
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
