import { Building2, Globe, Menu, Moon, ShieldCheck, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useEffect } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { useEnterpriseStore } from '../../stores/enterpriseStore';

export default function Header() {
  const { t } = useTranslation();
  const { language, darkMode, toggleLanguage, toggleDarkMode, toggleSidebar } = useUIStore();
  const { context, fetchContext, loading, setWorkspaceKey } = useEnterpriseStore();

  useEffect(() => {
    if (!context && !loading) {
      void fetchContext();
    }
  }, [context, fetchContext, loading]);

  const workspaces = context?.available_workspaces ?? [];
  const activeWorkspace = context?.workspace;
  const canSwitchWorkspace = workspaces.length > 1;

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded p-1.5 text-gray-500 hover:bg-gray-100 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
          aria-label="Toggle sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">D</span>
          </div>
          <span className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('app.title')}
          </span>
          <span className="text-xs text-gray-400 hidden sm:inline">{t('app.subtitle')}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 shadow-sm dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-100 lg:flex">
          <Building2 className="h-4 w-4" />
          <div className="min-w-[12rem]">
            <p className="truncate text-xs uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
              {t('enterprise.workspace')}
            </p>
            {canSwitchWorkspace ? (
              <select
                value={activeWorkspace?.slug ?? ''}
                onChange={(event) => {
                  void setWorkspaceKey(event.target.value);
                }}
                className="w-full bg-transparent text-sm font-semibold outline-none"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.slug} className="text-gray-900">
                    {workspace.name}
                  </option>
                ))}
              </select>
            ) : (
              <p className="truncate text-sm font-semibold">
                {activeWorkspace?.name ?? t('common.loading')}
              </p>
            )}
          </div>
        </div>

        {activeWorkspace && (
          <div className="hidden items-center gap-1 rounded-full bg-gray-100 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-700 dark:bg-gray-800 dark:text-gray-200 md:flex">
            <ShieldCheck className="h-3.5 w-3.5" />
            {activeWorkspace.role}
          </div>
        )}

        {context?.user && (
          <div className="hidden text-right md:block">
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
              {context.user.display_name}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {context.user.email}
            </p>
          </div>
        )}

        <button
          type="button"
          onClick={toggleLanguage}
          className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          title={t('common.language')}
        >
          <Globe className="h-4 w-4" />
          <span>{language === 'en' ? 'EN' : '中文'}</span>
        </button>

        <button
          type="button"
          onClick={toggleDarkMode}
          className="rounded p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
          title={t('common.darkMode')}
          aria-label={t('common.darkMode')}
        >
          {darkMode ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>
      </div>
    </header>
  );
}
