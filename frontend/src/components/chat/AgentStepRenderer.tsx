import { CheckCircle2, Circle, Loader2, ListChecks, Cpu, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { ChatStep, AgentTaskPlanStep } from '../../types';

export function PlanStep({ step }: { step: ChatStep }) {
  const planSteps = step.content as unknown as AgentTaskPlanStep[];
  if (!Array.isArray(planSteps)) return null;

  return (
    <div className="my-2">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1.5">
        <ListChecks size={12} />
        <span>Analysis Plan</span>
      </div>
      <div className="space-y-1">
        {planSteps.map((ps, i) => {
          const StatusIcon =
            ps.status === 'completed' ? CheckCircle2 :
            ps.status === 'running' ? Loader2 :
            ps.status === 'failed' ? Circle :
            Circle;
          const iconClass =
            ps.status === 'completed' ? 'text-green-500' :
            ps.status === 'running' ? 'text-blue-500 animate-spin' :
            ps.status === 'failed' ? 'text-red-500' :
            'text-gray-400 dark:text-gray-600';
          return (
            <div key={i} className="flex items-center gap-2 text-xs">
              <StatusIcon size={13} className={iconClass} />
              <span className={ps.status === 'completed' ? 'text-gray-500 line-through' : 'text-gray-700 dark:text-gray-300'}>
                {ps.index + 1}. {ps.description}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function AgentActionStep({ step }: { step: ChatStep }) {
  const content = step.content as Record<string, unknown>;
  return (
    <div className="my-1 flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 py-1">
      <Cpu size={12} />
      <span>{(content.description as string) || 'Executing step...'}</span>
      {step.streaming && <Loader2 size={12} className="animate-spin" />}
    </div>
  );
}

export function AgentProgressStep({ step }: { step: ChatStep }) {
  const content = step.content as Record<string, unknown>;
  const progress = (content.progress as number) ?? 0;
  const message = (content.message as string) ?? '';

  return (
    <div className="my-1.5">
      <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
        <span>{message}</span>
        <span className="font-mono">{Math.round(progress * 100)}%</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
        <div
          className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
    </div>
  );
}

export function SummaryStep({ step }: { step: ChatStep }) {
  return (
    <div className="my-2">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
        <FileText size={11} />
        <span>Analysis Summary</span>
      </div>
      <div className="text-sm text-gray-700 dark:text-gray-200 prose dark:prose-invert prose-sm max-w-none">
        <ReactMarkdown>{step.content as string}</ReactMarkdown>
      </div>
    </div>
  );
}
