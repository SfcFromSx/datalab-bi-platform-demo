import { Play, Trash2, ChevronUp, ChevronDown, Sparkles, Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useState } from 'react';
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
  isEditingAI?: boolean;
  aiProgress?: number;
  onRun: () => void;
  onDelete: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onEditAI?: (prompt: string) => void;
  isFirst?: boolean;
  isLast?: boolean;
}

export default function CellToolbar({
  cellType, isRunning, isEditingAI, aiProgress, onRun, onDelete, onMoveUp, onMoveDown, onEditAI, isFirst, isLast,
}: Props) {
  const { t } = useTranslation();
  const [showAIInput, setShowAIInput] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');

  const handleAISubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!aiPrompt.trim() || !onEditAI) return;
    onEditAI(aiPrompt);
    setAiPrompt('');
    setShowAIInput(false);
  };

  return (
    <div className="flex flex-col border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
      <div className="flex items-center gap-1.5 px-3 py-1.5">
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLORS[cellType]}`}>
          {t(`cell.${cellType}`)}
        </span>
        <div className="flex-1" />
        {onEditAI && (
          <button
            onClick={() => setShowAIInput(!showAIInput)}
            className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${showAIInput || isEditingAI ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300' : 'text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700'}`}
            title="Edit Cell with AI"
          >
            <Sparkles size={12} className={isEditingAI ? "animate-pulse" : ""} />
            {isEditingAI ? `AI ${Math.round((aiProgress ?? 0) * 100)}%` : 'AI Edit'}
          </button>
        )}
        <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-1" />
        <button onClick={onMoveUp} disabled={isFirst} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors" title={t('cell.moveUp')}>
          <ChevronUp size={14} />
        </button>
        <button onClick={onMoveDown} disabled={isLast} className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-30 transition-colors" title={t('cell.moveDown')}>
          <ChevronDown size={14} />
        </button>
        <button onClick={onRun} disabled={isRunning} className="flex items-center gap-1 px-2 py-1 flex-shrink-0 rounded text-xs font-medium bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 transition-colors">
          <Play size={12} />
          {isRunning ? t('cell.running') : t('cell.run')}
        </button>
        <button onClick={onDelete} className="p-1 rounded text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors" title={t('cell.delete')}>
          <Trash2 size={14} />
        </button>
      </div>

      {showAIInput && (
        <form onSubmit={handleAISubmit} className="px-3 pb-2 pt-1 flex gap-2 items-center animate-in slide-in-from-top-2">
          <div className="relative flex-1">
            <input
              autoFocus
              type="text"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="E.g. Add a WHERE clause to filter out refunded orders..."
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-white dark:bg-gray-900 border border-indigo-200 dark:border-indigo-800 rounded outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
            />
            <Sparkles size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-indigo-400" />
          </div>
          <button
            type="submit"
            disabled={!aiPrompt.trim()}
            className="p-1.5 rounded bg-indigo-500 text-white disabled:opacity-50 hover:bg-indigo-600 transition-colors"
          >
            <Send size={14} />
          </button>
        </form>
      )}
    </div>
  );
}
