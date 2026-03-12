import { CheckCircle2, ChevronDown, ChevronUp, LoaderCircle, MessageSquare, Sparkles, X, XCircle } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useModelUIStore } from '../../stores/modelUIStore';
import type { CellAIState } from '../../types';

interface Props {
  state: CellAIState;
  onClose: () => void;
  onClear: () => void;
}

const STAGES = ['context', 'dag', 'ipc', 'rewrite', 'generate', 'validate'];

function getStageSpecificInfo(stage: string, details?: any): Record<string, any> | null {
  if (!details) return null;
  switch (stage) {
    case 'context':
      return {
        path: details.workspace_dir,
        context: details.context_file,
        ancestors: details.ancestors?.length > 0 ? details.ancestors : null
      };
    case 'dag':
      return {
        plan: details.plan?.length > 0 ? details.plan : null
      };
    case 'ipc':
      return {
        deps: details.dependencies?.length > 0 ? details.dependencies : null,
        in: details.inbox_dir,
        out: details.outbox_dir,
        msgs: details.input_messages || details.published_messages ? `${details.input_messages || 0} in / ${details.published_messages || 0} out` : null
      };
    case 'rewrite':
      return {
        task: details.task_file,
        mode: details.mode
      };
    default:
      return null;
  }
}

export default function CellGenerationPanel({ state, onClose, onClear }: Props) {
  const { t } = useTranslation();
  const activeModelName = useModelUIStore((s) => s.activeModelName);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showDetails, setShowDetails] = useState(true);
  const [showDraft, setShowDraft] = useState(true);

  return (
    <aside className={`transition-all duration-300 ease-in-out border-gray-200 bg-gradient-to-b from-indigo-50 to-white dark:border-gray-700 dark:from-indigo-950/20 dark:to-gray-900 lg:border-l lg:border-t-0 p-4 ${isCollapsed ? 'h-auto lg:w-12 lg:p-2' : 'h-full lg:w-80'
      }`}>
      <div className={`flex items-start justify-between gap-3 ${isCollapsed ? 'lg:flex-col lg:items-center' : ''}`}>
        <div
          className={`flex-1 cursor-pointer select-none ${isCollapsed ? 'lg:mt-2' : ''}`}
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          <p className={`text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-600 dark:text-indigo-300 transition-all ${isCollapsed ? 'lg:[writing-mode:vertical-lr] lg:rotate-180 lg:mb-4' : 'mb-1'}`}>
            LLM Progress
          </p>
          {!isCollapsed && (
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
              {state.message}
            </p>
          )}
        </div>
        <div className={`flex gap-1 ${isCollapsed ? 'lg:flex-col items-center' : ''}`}>
          <button
            type="button"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
            title={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? <ChevronDown className="h-4 w-4 lg:hidden" /> : <ChevronUp className="h-4 w-4 lg:hidden" />}
            {isCollapsed ? <ChevronUp className="h-4 w-4 hidden lg:block rotate-90" /> : <ChevronDown className="h-4 w-4 hidden lg:block -rotate-90" />}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-gray-200"
            title="Hide Progress"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          <div className="mt-4 h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${state.status === 'error' ? 'bg-red-500' : 'bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]'
                }`}
              style={{ width: `${Math.max(4, state.progress * 100)}%` }}
            />
          </div>

          {activeModelName && (
            <p className="mt-2 text-[10px] text-gray-500 dark:text-gray-400">
              {t('cell.usingModel', 'Using model')}: <span className="font-medium text-indigo-600 dark:text-indigo-400">{activeModelName}</span>
              {' · '}
              <span className="italic">{t('cell.switchModelInHeader', 'Switch in header')}</span>
            </p>
          )}

          {state.prompt && (
            <div className="mt-4 p-3 bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100/50 dark:border-indigo-800/30 rounded-xl">
              <div className="flex items-center gap-2 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-500 dark:text-indigo-400">
                <MessageSquare className="w-3 h-3" />
                User Request
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300 italic leading-relaxed">
                "{state.prompt}"
              </p>
            </div>
          )}

          <div className="mt-4 space-y-4">
            <div>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex w-full items-center justify-between mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 transition-colors"
                title={showDetails ? "Fold Details" : "Unfold Details"}
              >
                <span>Progress Details</span>
                {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {showDetails && (
                <div className="space-y-2 animate-in slide-in-from-top-1">
                  {STAGES.map((stage) => {
                    const active = state.stage === stage;
                    const completed =
                      STAGES.indexOf(stage) < STAGES.indexOf(state.stage) || state.status === 'completed';

                    const stageDetails = getStageSpecificInfo(stage, state.details);
                    const hasDetails = stageDetails && Object.keys(stageDetails).length > 0;

                    const content = (
                      <div
                        className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors ${active ? 'bg-indigo-100 text-indigo-900 dark:bg-indigo-900/40 dark:text-indigo-100' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50'
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
                        {hasDetails && (
                          <span className="ml-auto text-[10px] font-medium text-indigo-400 dark:text-indigo-500">
                            DETAILS
                          </span>
                        )}
                      </div>
                    );

                    if (hasDetails) {
                      return (
                        <details key={stage} className="group">
                          <summary className="list-none focus:outline-none">
                            {content}
                          </summary>
                          <div className="ml-8 mt-1 space-y-1.5 border-l-2 border-indigo-100/50 pl-3 pt-1 text-xs text-indigo-900/70 dark:border-indigo-200/60">
                            {Object.entries(stageDetails).map(([key, value]) => (
                              <div key={key} className="break-all font-mono">
                                <span className="font-semibold uppercase text-indigo-500/80 dark:text-indigo-400/60">{key}:</span>
                                <span className="ml-1 text-[11px]">
                                  {Array.isArray(value) ? value.join(', ') : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </details>
                      );
                    }

                    return <div key={stage}>{content}</div>;
                  })}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 bg-white/80 p-3 dark:border-gray-700 dark:bg-gray-950/60">
              <button
                onClick={() => setShowDraft(!showDraft)}
                className="flex w-full items-center justify-between text-xs font-semibold uppercase tracking-[0.16em] text-gray-500 hover:text-gray-400 dark:text-gray-400 transition-colors"
                title={showDraft ? "Fold Draft" : "Unfold Draft"}
              >
                <span>Draft Preview</span>
                {showDraft ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {showDraft && (
                <pre className="mt-2 max-h-72 overflow-auto animate-in slide-in-from-top-1 whitespace-pre-wrap break-words text-xs text-gray-700 dark:text-gray-200">
                  {state.draft || 'Waiting for the first model tokens...'}
                </pre>
              )}
            </div>
          </div>

          {(state.status === 'completed' || state.status === 'error') && (
            <div className={`mt-4 rounded-xl border p-3 ${state.status === 'error' ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30' : 'border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30'}`}>
              <div className="flex items-start gap-2">
                {state.status === 'error' ? (
                  <XCircle className="h-4 w-4 shrink-0 text-red-500 mt-0.5" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${state.status === 'error' ? 'text-red-800 dark:text-red-200' : 'text-emerald-800 dark:text-emerald-200'}`}>
                    {state.status === 'error' ? 'Failed' : 'Success'}
                  </p>
                  <p className={`mt-1 text-xs break-words ${state.status === 'error' ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300'}`}>
                    {state.error || state.message}
                  </p>
                </div>
              </div>
              <button
                onClick={onClear}
                className={`mt-3 w-full rounded-lg px-3 py-1.5 text-xs font-semibold transition ${state.status === 'error'
                  ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/40 dark:text-red-300 dark:hover:bg-red-900/60'
                  : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-900/60'}`}
              >
                Dismiss & Clear
              </button>
            </div>
          )}
        </>
      )}
    </aside>
  );
}
