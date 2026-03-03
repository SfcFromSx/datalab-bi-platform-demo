import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, BookOpen, Upload, Plus, Trash2 } from 'lucide-react';
import { useNotebookStore } from '../../stores/notebookStore';
import { listDataSources, uploadCSV } from '../../services/api';
import type { DataSource, NotebookListItem } from '../../types';
import { useState } from 'react';

interface Props {
  onSelectNotebook: (id: string) => void;
  activeNotebookId?: string;
}

export default function Sidebar({ onSelectNotebook, activeNotebookId }: Props) {
  const { t } = useTranslation();
  const { notebooks, fetchNotebooks, createNotebook } = useNotebookStore();
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeTab, setActiveTab] = useState<'notebooks' | 'data'>('notebooks');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchNotebooks();
    listDataSources().then(setDataSources).catch(() => {});
  }, [fetchNotebooks]);

  const handleCreateNotebook = async () => {
    const nb = await createNotebook();
    if (nb) onSelectNotebook(nb.id);
  };

  const handleUploadCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const ds = await uploadCSV(file);
      setDataSources((prev) => [...prev, ds]);
    } catch (err) {
      console.error('Upload failed:', err);
    }
    e.target.value = '';
  };

  return (
    <div className="w-64 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('notebooks')}
          className={`flex-1 px-3 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'notebooks' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          <BookOpen size={14} /> {t('sidebar.notebooks')}
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={`flex-1 px-3 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'data' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          <Database size={14} /> {t('sidebar.dataSources')}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {activeTab === 'notebooks' && (
          <div className="space-y-1">
            <button onClick={handleCreateNotebook} className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
              <Plus size={14} /> {t('notebook.newNotebook')}
            </button>
            {notebooks.map((nb) => (
              <button
                key={nb.id}
                onClick={() => onSelectNotebook(nb.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${nb.id === activeNotebookId ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
              >
                <div className="truncate">{nb.title}</div>
                <div className="text-xs text-gray-400 mt-0.5">{nb.cell_count} cells</div>
              </button>
            ))}
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-1">
            <button onClick={() => fileInputRef.current?.click()} className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
              <Upload size={14} /> {t('sidebar.uploadCSV')}
            </button>
            <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleUploadCSV} />
            {dataSources.length === 0 ? (
              <div className="px-3 py-4 text-sm text-gray-400 text-center">{t('sidebar.noData')}</div>
            ) : (
              dataSources.map((ds) => (
                <div key={ds.id} className="px-3 py-2 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
                  <div className="flex items-center gap-2">
                    <Database size={14} className="text-gray-400" />
                    <span className="truncate">{ds.name}</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">{ds.ds_type}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
