import { CheckCircle2, LoaderCircle, Sparkles, X, XCircle } from 'lucide-react';
import type { CellAIState } from '../../types';

interface Props {
  state: CellAIState;
  onClose: () => void;
}

const STAGES = ['context', 'dag', 'ipc', 'rewrite', 'generate', 'validate', 'done'];

export default function CellGenerationPanel({ state, onClose }: Props) {
  return (
    <aside className="w-full border-t border-gray-200 bg-gradient-to-b from-indigo-50 to-white p-4 dark:border-gray-700 dark:from-indigo-950/20 dark:to-gray-900 lg:w-80 lg:border-l lg:border-t-0">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-300">
            LLM Progress
          </p>
          <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-gray-100">
            {state.message}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 h-2 rounded-full bg-gray-200 dark:bg-gray-800">
        <div
          className={`h-2 rounded-full transition-all ${
            state.status === 'error' ? 'bg-red-500' : 'bg-indigo-500'
          }`}
          style={{ width: `${Math.max(4, state.progress * 100)}%` }}
        />
      </div>

      <div className="mt-4 space-y-2">
        {STAGES.map((stage) => {
          const active = state.stage === stage;
          const completed =
            STAGES.indexOf(stage) < STAGES.indexOf(state.stage) || state.status === 'completed';
          return (
            <div
              key={stage}
              className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm ${
                active ? 'bg-indigo-100 text-indigo-900 dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {completed ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              ) : active ? (
                <LoaderCircle className="h-4 w-4 animate-spin text-indigo-500" />
              ) : state.status === 'error' && stage === 'generate' ? (
                <XCircle className="h-4 w-4 text-red-500" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              <span className="capitalize">{stage}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-4 rounded-xl border border-gray-200 bg-white/80 p-3 dark:border-gray-700 dark:bg-gray-950/60">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
          Draft
        </p>
        <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs text-gray-700 dark:text-gray-200">
          {state.draft || 'Waiting for the first model tokens...'}
        </pre>
      </div>

      {state.details && (
        <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/70 p-3 text-xs text-indigo-950 dark:border-indigo-900/60 dark:bg-indigo-950/20 dark:text-indigo-100">
          <p className="font-semibold uppercase tracking-[0.16em] text-indigo-600 dark:text-indigo-300">
            Cell Agent
          </p>
          <div className="mt-2 space-y-2">
            <p>
              <span className="font-semibold">Mode:</span> {state.details.mode}
            </p>
            <p>
              <span className="font-semibold">Workspace:</span> {state.details.workspace_dir}
            </p>
            <p>
              <span className="font-semibold">Dependencies:</span> {state.details.dependencies.length > 0 ? state.details.dependencies.join(', ') : 'none'}
            </p>
            <p>
              <span className="font-semibold">Plan:</span> {state.details.plan.join(' -> ')}
            </p>
          </div>
        </div>
      )}

      {state.error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300">
          {state.error}
        </div>
      )}
    </aside>
  );
}
