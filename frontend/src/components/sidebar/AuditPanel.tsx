import { RefreshCw, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { AuditEvent } from '../../types';

interface Props {
  auditEvents: AuditEvent[];
  auditLoading: boolean;
  onRefresh: () => void;
}

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString();
}

export default function AuditPanel({ auditEvents, auditLoading, onRefresh }: Props) {
  const { t } = useTranslation();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between px-3 pt-1">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-600">
            {t('enterprise.audit')}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t('enterprise.auditDescription')}
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="rounded-lg border border-gray-200 p-2 text-gray-500 transition hover:border-emerald-300 hover:text-emerald-600 dark:border-gray-700 dark:text-gray-300 dark:hover:border-emerald-700 dark:hover:text-emerald-300"
          title={t('enterprise.refreshAudit')}
        >
          <RefreshCw className={`h-4 w-4 ${auditLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {auditEvents.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 px-3 py-6 text-center text-sm text-gray-400 dark:border-gray-700">
          {t('enterprise.noAuditEvents')}
        </div>
      ) : (
        <div className="space-y-2">
          {auditEvents.map((event) => (
            <div
              key={event.id}
              className="rounded-xl border border-gray-200 bg-white/90 p-3 shadow-sm dark:border-gray-700 dark:bg-gray-900/60"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {event.action}
                    </p>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {event.actor_email ?? t('enterprise.systemActor')}
                  </p>
                </div>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
                  {event.status}
                </span>
              </div>

              <div className="mt-3 space-y-1 text-xs text-gray-500 dark:text-gray-400">
                <p>{event.resource_type}{event.resource_id ? ` · ${event.resource_id}` : ''}</p>
                <p>{formatTimestamp(event.created_at)}</p>
                <p className="truncate">req {event.request_id}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
