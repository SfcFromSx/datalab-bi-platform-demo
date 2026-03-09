import type { CellAgentRuntimeInfo } from '../../types';

interface Props {
  runtime: CellAgentRuntimeInfo;
}

export default function CellRuntimeCard({ runtime }: Props) {
  return (
    <details className="border-t border-gray-100 bg-slate-50/80 px-4 py-3 text-xs text-slate-700 dark:border-gray-800 dark:bg-slate-950/30 dark:text-slate-200">
      <summary className="cursor-pointer font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">
        Cell Runtime Details
      </summary>
      <div className="mt-3 space-y-2">
        <p>
          <span className="font-semibold">Cell ID:</span> {runtime.cell_id || 'unknown'}
        </p>
        <p>
          <span className="font-semibold">Mode:</span> {runtime.mode}
        </p>
        <p>
          <span className="font-semibold">Workspace:</span> {runtime.workspace_dir}
        </p>
        <p>
          <span className="font-semibold">Dependencies:</span> {runtime.dependencies.length > 0 ? runtime.dependencies.join(', ') : 'none'}
        </p>
        <p>
          <span className="font-semibold">Ancestors:</span> {runtime.ancestors.length > 0 ? runtime.ancestors.join(', ') : 'none'}
        </p>
        <p>
          <span className="font-semibold">Plan:</span> {runtime.plan.join(' -> ')}
        </p>
        <p>
          <span className="font-semibold">Messages:</span> {runtime.input_messages ?? 0} in / {runtime.published_messages ?? 0} out
        </p>
      </div>
    </details>
  );
}
