import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Cpu,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Ban,
  Zap,
  Database,
  FileText,
  RefreshCw,
} from 'lucide-react';
import { useAgentTaskStore } from '../../stores/agentTaskStore';
import type { AgentTask, AgentTaskStatus } from '../../types';

const STATUS_CONFIG: Record<
  string,
  { icon: typeof CheckCircle2; color: string; bg: string }
> = {
  pending: { icon: Clock, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/30' },
  running: { icon: Loader2, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30' },
  completed: { icon: CheckCircle2, color: 'text-green-600 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/30' },
  failed: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30' },
  cancelled: { icon: Ban, color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800' },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.color}`}>
      <Icon size={12} className={status === 'running' ? 'animate-spin' : ''} />
      {status}
    </span>
  );
}

function formatDuration(start: string, end: string) {
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60_000).toFixed(1)}m`;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleString();
}

function TaskCard({ task }: { task: AgentTask }) {
  const { cancelTask } = useAgentTaskStore();
  const canCancel = task.status === 'pending' || task.status === 'running';

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0 mr-3">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {task.query}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {formatTime(task.created_at)}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>

      {task.status === 'running' && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span>Progress</span>
            <span>{Math.round(task.progress * 100)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.round(task.progress * 100)}%` }}
            />
          </div>
        </div>
      )}

      {task.plan && task.plan.length > 0 && (
        <div className="mb-3 text-xs space-y-0.5">
          {task.plan.map((step, i) => {
            const done = step.status === 'completed';
            const running = step.status === 'running';
            return (
              <div key={i} className={`flex items-center gap-1.5 ${done ? 'text-gray-400' : 'text-gray-600 dark:text-gray-300'}`}>
                {done ? <CheckCircle2 size={11} className="text-green-500" /> :
                 running ? <Loader2 size={11} className="text-blue-500 animate-spin" /> :
                 <Clock size={11} className="text-gray-400" />}
                <span className={done ? 'line-through' : ''}>{step.description}</span>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1">
          <Zap size={11} />
          {task.tokens_used.toLocaleString()} tokens
        </span>
        <span className="flex items-center gap-1">
          <Database size={11} />
          {task.queries_executed} queries
        </span>
        <span className="flex items-center gap-1">
          <FileText size={11} />
          {task.cells_created} cells
        </span>
        {task.status !== 'pending' && task.status !== 'running' && (
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {formatDuration(task.created_at, task.updated_at)}
          </span>
        )}
      </div>

      {task.error && (
        <div className="mt-2 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-2 py-1 rounded">
          {task.error}
        </div>
      )}

      {canCancel && (
        <button
          onClick={() => cancelTask(task.id)}
          className="mt-3 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
        >
          Cancel task
        </button>
      )}
    </div>
  );
}

function ResourceSummary({ tasks }: { tasks: AgentTask[] }) {
  const totalTokens = tasks.reduce((sum, t) => sum + t.tokens_used, 0);
  const totalQueries = tasks.reduce((sum, t) => sum + t.queries_executed, 0);
  const totalCells = tasks.reduce((sum, t) => sum + t.cells_created, 0);
  const completed = tasks.filter((t) => t.status === 'completed').length;
  const failed = tasks.filter((t) => t.status === 'failed').length;

  const stats = [
    { label: 'Total Tasks', value: tasks.length, icon: Cpu },
    { label: 'Completed', value: completed, icon: CheckCircle2 },
    { label: 'Failed', value: failed, icon: XCircle },
    { label: 'Tokens Used', value: totalTokens.toLocaleString(), icon: Zap },
    { label: 'Queries Run', value: totalQueries, icon: Database },
    { label: 'Cells Created', value: totalCells, icon: FileText },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {stats.map((s) => (
        <div
          key={s.label}
          className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center"
        >
          <s.icon size={18} className="mx-auto text-gray-400 dark:text-gray-500 mb-1" />
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">{s.value}</div>
          <div className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-gray-400">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

export default function AgentStatusPage() {
  const { t } = useTranslation();
  const { tasks, total, isLoading, fetchTasks } = useAgentTaskStore();
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    fetchTasks(filter ? { status: filter } : undefined);
  }, [fetchTasks, filter]);

  useEffect(() => {
    const hasActive = tasks.some((t) => t.status === 'running' || t.status === 'pending');
    if (!hasActive) return;

    const interval = setInterval(() => {
      fetchTasks(filter ? { status: filter } : undefined);
    }, 3000);
    return () => clearInterval(interval);
  }, [tasks, filter, fetchTasks]);

  const runningTasks = tasks.filter((t) => t.status === 'running' || t.status === 'pending');
  const completedTasks = tasks.filter((t) => t.status !== 'running' && t.status !== 'pending');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            to="/"
            className="p-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            <ArrowLeft size={18} className="text-gray-600 dark:text-gray-400" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Cpu size={24} />
              {t('agents.title', 'Agent Tasks')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('agents.subtitle', 'Monitor and manage autonomous analysis tasks')}
            </p>
          </div>
          <button
            onClick={() => fetchTasks(filter ? { status: filter } : undefined)}
            disabled={isLoading}
            className="ml-auto p-2 rounded-lg bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={`text-gray-600 dark:text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Resource Summary */}
        <ResourceSummary tasks={tasks} />

        {/* Filter */}
        <div className="flex gap-2 mb-6">
          {['', 'running', 'completed', 'failed', 'cancelled'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === f
                  ? 'bg-blue-500 text-white'
                  : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
              }`}
            >
              {f || 'All'}
            </button>
          ))}
        </div>

        {/* Running Tasks */}
        {runningTasks.length > 0 && (
          <div className="mb-8">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-blue-500" />
              {t('agents.running', 'Running Tasks')} ({runningTasks.length})
            </h2>
            <div className="grid gap-3 md:grid-cols-2">
              {runningTasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          </div>
        )}

        {/* Task History */}
        <div>
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-3">
            {t('agents.history', 'Task History')} ({completedTasks.length})
          </h2>
          {completedTasks.length === 0 && !isLoading ? (
            <div className="text-center py-12 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700">
              <Cpu size={32} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
              <p className="text-sm text-gray-500">{t('agents.noTasks', 'No agent tasks yet')}</p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {completedTasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
