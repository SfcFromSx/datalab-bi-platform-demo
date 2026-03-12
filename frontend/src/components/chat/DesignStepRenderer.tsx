import { CheckCircle2, Circle, AlertCircle, Plus, Pencil, Trash2, Move, Play } from 'lucide-react';
import type { ChatStep, DesignAction } from '../../types';

const ACTION_ICONS: Record<string, typeof Plus> = {
  add_cell: Plus,
  edit_cell: Pencil,
  delete_cell: Trash2,
  move_cell: Move,
  execute_cell: Play,
};

const ACTION_LABELS: Record<string, string> = {
  add_cell: 'Add Cell',
  edit_cell: 'Edit Cell',
  delete_cell: 'Delete Cell',
  move_cell: 'Move Cell',
  execute_cell: 'Execute Cell',
};

export function ActionStep({ step }: { step: ChatStep }) {
  const action = step.content as DesignAction;
  const Icon = ACTION_ICONS[action.action] || Circle;
  const label = ACTION_LABELS[action.action] || action.action;
  const applied = step.applied;

  return (
    <div className={`my-1.5 flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${
      applied
        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
        : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
    }`}>
      <Icon size={14} className={applied ? 'text-green-600 dark:text-green-400 mt-0.5' : 'text-blue-600 dark:text-blue-400 mt-0.5'} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{label}</span>
          {action.cell_type && (
            <span className="px-1.5 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-[10px] uppercase">
              {action.cell_type}
            </span>
          )}
          {applied ? (
            <CheckCircle2 size={13} className="text-green-600 dark:text-green-400 ml-auto" />
          ) : (
            <Circle size={13} className="text-blue-400 dark:text-blue-500 ml-auto animate-pulse" />
          )}
        </div>
        {action.description && (
          <p className="text-gray-600 dark:text-gray-400 mt-0.5">{action.description}</p>
        )}
        {action.source && (
          <pre className="mt-1 text-[10px] font-mono bg-gray-100 dark:bg-gray-800 p-1.5 rounded max-h-24 overflow-auto whitespace-pre-wrap">
            {action.source.slice(0, 300)}{action.source.length > 300 ? '...' : ''}
          </pre>
        )}
      </div>
    </div>
  );
}

export function ActionResultStep({ step }: { step: ChatStep }) {
  const content = step.content as string;
  const isError = content.startsWith('Error:');
  return (
    <div className={`my-1 px-3 py-1.5 text-xs rounded-lg ${
      isError
        ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
        : 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
    }`}>
      {isError ? <AlertCircle size={12} className="inline mr-1" /> : <CheckCircle2 size={12} className="inline mr-1" />}
      {content}
    </div>
  );
}
