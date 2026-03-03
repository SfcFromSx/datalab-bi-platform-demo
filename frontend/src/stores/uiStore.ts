import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import i18n from '../i18n';

export type Language = 'en' | 'zh';

interface UIState {
  language: Language;
  darkMode: boolean;
  sidebarOpen: boolean;
  chatOpen: boolean;
}

interface UIActions {
  toggleLanguage: () => void;
  toggleDarkMode: () => void;
  toggleSidebar: () => void;
  toggleChat: () => void;
}

function syncDarkMode(dark: boolean) {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', dark);
  }
}

export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set, get) => ({
      language: 'en' as Language,
      darkMode: false,
      sidebarOpen: true,
      chatOpen: false,

      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),

      toggleLanguage: () => {
        const next: Language = get().language === 'en' ? 'zh' : 'en';
        set({ language: next });
        void i18n.changeLanguage(next);
      },

      toggleDarkMode: () => {
        const next = !get().darkMode;
        set({ darkMode: next });
        syncDarkMode(next);
      },
    }),
    {
      name: 'datalab-ui',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ language: s.language, darkMode: s.darkMode }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          void i18n.changeLanguage(state.language);
          syncDarkMode(state.darkMode);
        }
      },
    }
  )
);
