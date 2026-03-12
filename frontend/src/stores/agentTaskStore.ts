import { create } from 'zustand';
import type { AgentTask } from '../types';
import { listAgentTasks, getAgentTask, cancelAgentTask } from '../services/api';

interface AgentTaskState {
  tasks: AgentTask[];
  total: number;
  selectedTask: AgentTask | null;
  isLoading: boolean;
  error: string | null;
}

interface AgentTaskActions {
  fetchTasks: (params?: { status?: string; limit?: number; offset?: number }) => Promise<void>;
  fetchTask: (id: string) => Promise<void>;
  cancelTask: (id: string) => Promise<void>;
  clearSelected: () => void;
}

export const useAgentTaskStore = create<AgentTaskState & AgentTaskActions>((set) => ({
  tasks: [],
  total: 0,
  selectedTask: null,
  isLoading: false,
  error: null,

  fetchTasks: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const data = await listAgentTasks(params);
      set({ tasks: data.tasks, total: data.total, isLoading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch tasks', isLoading: false });
    }
  },

  fetchTask: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const task = await getAgentTask(id);
      set({ selectedTask: task, isLoading: false });
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch task', isLoading: false });
    }
  },

  cancelTask: async (id) => {
    try {
      await cancelAgentTask(id);
      set((s) => ({
        tasks: s.tasks.map((t) => (t.id === id ? { ...t, status: 'cancelled' as const } : t)),
      }));
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to cancel task' });
    }
  },

  clearSelected: () => set({ selectedTask: null }),
}));
