import { create } from 'zustand';

interface ModelUIState {
  activeModelName: string | null;
  setActiveModelName: (name: string | null) => void;
}

export const useModelUIStore = create<ModelUIState>((set) => ({
  activeModelName: null,
  setActiveModelName: (name) => set({ activeModelName: name }),
}));
