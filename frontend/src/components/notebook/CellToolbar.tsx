import { Play, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { CellType } from '../../types';

const TYPE_COLORS: Record<CellType, string> = {
  sql: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  python: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  chart: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  markdown: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
};

interface Props {
  cellType: CellType;
  isRunning?: boolean;
  onRun: () => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export default function CellToolbar({
  cellType, isRunning, onRun, onDelete, onMoveUp, onMoveDown, isFirst, isLast,
}: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[cellType]}`}>
        {t(`cell.${cellType}`)}
      </span>
      <div className="flex-1" />
      <button onClick={onMoveUp} disabled={isFirst} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors" title={t('cell.moveUp')}>
        <ChevronUp size={14} />
      </button>
      <button onClick={onMoveDown} disabled={isLast} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors" title={t('cell.moveDown')}>
        <ChevronDown size={14} />
      </button>
      {cellType !== 'chart' && (
        <button onClick={onRun} disabled={isRunning} className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 transition-colors">
          <Play size={12} />
          {isRunning ? t('cell.running') : t('cell.run')}
        </button>
      )}
      <button onClick={onDelete} className="p-1 rounded text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors" title={t('cell.delete')}>
        <Trash2 size={14} />
      </button>
    </div>
  );
}
