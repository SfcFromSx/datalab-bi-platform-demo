import { Globe, Menu, Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useUIStore } from '../../stores/uiStore';

export default function Header() {
  const { t } = useTranslation();
  const { language, darkMode, toggleLanguage, toggleDarkMode, toggleSidebar } = useUIStore();

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
