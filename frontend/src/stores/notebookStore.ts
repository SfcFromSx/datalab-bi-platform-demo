import { create } from 'zustand';
import type { Cell, CellType, Notebook, NotebookListItem } from '../types';
import {
  listNotebooks,
  createNotebook as createNotebookApi,
  getNotebook,
  createCell as createCellApi,
  updateCell as updateCellApi,
  deleteCellApi,
  moveCell as moveCellApi,
  executeCell as executeCellApi,
} from '../services/api';

interface NotebookState {
  notebooks: NotebookListItem[];
  activeNotebook: Notebook | null;
  cells: Cell[];
  loading: boolean;
  error: string | null;
}

interface NotebookActions {
  fetchNotebooks: () => Promise<void>;
  createNotebook: (title?: string, description?: string) => Promise<Notebook | null>;
  loadNotebook: (id: string) => Promise<void>;
  addCell: (cell_type: CellType, source?: string, position?: number) => Promise<Cell | null>;
  updateCellSource: (cellId: string, source: string) => Promise<void>;
  deleteCell: (cellId: string) => Promise<void>;
  moveCell: (cellId: string, position: number) => Promise<void>;
  executeCell: (cellId: string, source?: string) => Promise<void>;
  setCells: (cells: Cell[]) => void;
}

export const useNotebookStore = create<NotebookState & NotebookActions>((set, get) => ({
  notebooks: [],
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

  createNotebook: async (title = 'Untitled Notebook', description = '') => {
    set({ loading: true, error: null });
    try {
      const notebook = await createNotebookApi(title, description);
      const listItem: NotebookListItem = {
        id: notebook.id,
        title: notebook.title,
        description: notebook.description,
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
}));
