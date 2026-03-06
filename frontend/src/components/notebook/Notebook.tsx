import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNotebookStore } from '../../stores/notebookStore';
import CellContainer from './CellContainer';
import AddCellButton from './AddCellButton';
import LoadingSpinner from '../common/LoadingSpinner';
import { wsClient } from '../../services/websocket';

interface Props {
  notebookId: string;
}

export default function Notebook({ notebookId }: Props) {
  const { activeNotebook, cells, loading, loadNotebook } = useNotebookStore();
  const { t } = useTranslation();

  useEffect(() => {
    loadNotebook(notebookId);
    wsClient.connect(notebookId);
    return () => {
      wsClient.disconnect();
    };
  }, [notebookId, loadNotebook]);

  if (loading && !activeNotebook) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!activeNotebook) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Notebook not found
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {activeNotebook.title}
        </h1>
        {activeNotebook.description && (
          <p className="mt-1 text-sm text-gray-500">{activeNotebook.description}</p>
        )}
      </div>

      <div className="space-y-4">
        {cells.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg">{t('notebook.empty')}</p>
          </div>
        ) : (
          cells.map((cell, index) => (
            <CellContainer
              key={cell.id}
              cell={cell}
              index={index}
              totalCells={cells.length}
            />
          ))
        )}

        <AddCellButton />
      </div>
    </div>
  );
}
