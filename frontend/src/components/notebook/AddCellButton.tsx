import { useState } from 'react';
import { Plus, Database, Code, BarChart3, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { CellType } from '../../types';
import { useNotebookStore } from '../../stores/notebookStore';

const CELL_OPTIONS: { type: CellType; icon: typeof Code; label: string }[] = [
  { type: 'sql', icon: Database, label: 'cell.sql' },
  { type: 'python', icon: Code, label: 'cell.python' },
  { type: 'chart', icon: BarChart3, label: 'cell.chart' },
  { type: 'markdown', icon: FileText, label: 'cell.markdown' },
];

export default function AddCellButton() {
  const [isOpen, setIsOpen] = useState(false);
  const { addCell } = useNotebookStore();
  const { t } = useTranslation();

  const handleAdd = async (type: CellType) => {
    const defaults: Record<CellType, string> = {
      sql: 'SELECT * FROM ',
      python: 'import pandas as pd\n\n',
      chart: '{\n  "title": { "text": "Chart" },\n  "xAxis": { "type": "category", "data": ["A", "B", "C"] },\n  "yAxis": { "type": "value" },\n  "series": [{ "data": [10, 20, 30], "type": "bar" }]\n}',
      markdown: '# Title\n\nWrite your notes here...',
    };
    await addCell(type, defaults[type]);
    setIsOpen(false);
  };

  return (
    <div className="flex justify-center py-3">
      {isOpen ? (
        <div className="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          {CELL_OPTIONS.map(({ type, icon: Icon, label }) => (
            <button
              key={type}
              onClick={() => handleAdd(type)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <Icon size={16} />
              {t(label)}
            </button>
          ))}
          <button
            onClick={() => setIsOpen(false)}
            className="px-2 py-1 text-xs text-gray-400 hover:text-gray-600"
          >
            {t('common.cancel')}
          </button>
        </div>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm text-gray-500 border border-dashed border-gray-300 dark:border-gray-600 hover:border-brand-400 hover:text-brand-500 transition-colors"
        >
          <Plus size={16} />
          {t('notebook.addCell')}
        </button>
      )}
    </div>
  );
}
