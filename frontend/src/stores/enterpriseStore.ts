import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { AuditEvent, EnterpriseContext } from '../types';
import {
  getEnterpriseContext,
  listAuditEvents,
  setStoredUserEmail,
  setStoredWorkspaceKey,
} from '../services/api';

interface EnterpriseState {
  workspaceKey: string | null;
  userEmail: string | null;
  context: EnterpriseContext | null;
  auditEvents: AuditEvent[];
  loading: boolean;
  auditLoading: boolean;
  error: string | null;
}

interface EnterpriseActions {
  fetchContext: () => Promise<void>;
  refreshAudit: () => Promise<void>;
  setWorkspaceKey: (workspaceKey: string) => Promise<void>;
}

export const useEnterpriseStore = create<EnterpriseState & EnterpriseActions>()(
  persist(
    (set, get) => ({
      workspaceKey: null,
      userEmail: null,
      context: null,
      auditEvents: [],
      loading: false,
      auditLoading: false,
      error: null,

      fetchContext: async () => {
        set({ loading: true, error: null });
        try {
          const context = await getEnterpriseContext();
          setStoredWorkspaceKey(context.workspace.slug);
          setStoredUserEmail(context.user.email);
          set({
            workspaceKey: context.workspace.slug,
            userEmail: context.user.email,
            context,
            loading: false,
          });
        } catch (error) {
          set({
            loading: false,
            error: error instanceof Error ? error.message : 'Failed to load enterprise context',
          });
        }
      },

      refreshAudit: async () => {
        const role = get().context?.workspace.role;
        if (!role || !['owner', 'admin'].includes(role)) {
          set({ auditEvents: [] });
          return;
        }
        set({ auditLoading: true, error: null });
        try {
          const auditEvents = await listAuditEvents();
          set({ auditEvents, auditLoading: false });
        } catch (error) {
          set({
            auditLoading: false,
            error: error instanceof Error ? error.message : 'Failed to load audit events',
          });
        }
      },

      setWorkspaceKey: async (workspaceKey: string) => {
        setStoredWorkspaceKey(workspaceKey);
        set({ workspaceKey, context: null, auditEvents: [] });
        await get().fetchContext();
      },
    }),
    {
      name: 'datalab-enterprise',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        workspaceKey: state.workspaceKey,
        userEmail: state.userEmail,
      }),
    }
  )
);
