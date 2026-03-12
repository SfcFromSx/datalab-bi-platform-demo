import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileText, Clock, CheckCircle2, XCircle, AlertCircle, Database, Search, Filter, X } from 'lucide-react';
import { LLMLog, LLMLogStats } from '../../types';
import { listLLMLogs, getLLMLog, getLLMLogStats } from '../../services/api';

export default function ProcessHistoryPage() {
  const { t } = useTranslation();
  
  const [logs, setLogs] = useState<LLMLog[]>([]);
  const [stats, setStats] = useState<LLMLogStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [featureFilter, setFeatureFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(0);
  const limit = 20;
  const [total, setTotal] = useState(0);

  const [selectedLog, setSelectedLog] = useState<LLMLog | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchLogs(0);
  }, [featureFilter, statusFilter]);

  const fetchStats = async () => {
    setStatsLoading(true);
    try {
      const data = await getLLMLogStats();
      setStats(data);
    } catch (err: any) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setStatsLoading(false);
    }
  };

  const fetchLogs = async (pageNum: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listLLMLogs({
        feature: featureFilter || undefined,
        status: statusFilter || undefined,
        limit,
        offset: pageNum * limit,
      });
      if (pageNum === 0) {
        setLogs(data.logs);
      } else {
        setLogs(prev => [...prev, ...data.logs]);
      }
      setTotal(data.total);
      setPage(pageNum);
    } catch (err: any) {
      setError(t('common.error', 'An error occurred'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const openLogDetails = async (id: string) => {
    setDetailsLoading(true);
    setSelectedLog(null); // open modal with loading state
    try {
      const data = await getLLMLog(id);
      setSelectedLog(data);
    } catch (err: any) {
      console.error('Failed to fetch full log details:', err);
    } finally {
      setDetailsLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50/50 dark:bg-gray-900 flex flex-col items-center">
      <div className="w-full max-w-6xl px-4 py-8 space-y-8">
        
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
            {t('history.title', 'Process History')}
          </h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {t('history.subtitle', 'View records of AI Assistant and AI Edit processes')}
          </p>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-lg">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('history.totalCalls', 'Total Calls')}</p>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading ? '-' : stats?.total_calls.toLocaleString()}
              </h3>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-4">
            <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-lg">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('history.successRate', 'Success Rate')}</p>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading || !stats || stats.total_calls === 0 ? '-' : `${((stats.success_count / stats.total_calls) * 100).toFixed(1)}%`}
              </h3>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-4">
            <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-lg">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('history.totalTokens', 'Total Tokens')}</p>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading || !stats ? '-' : (stats.total_prompt_tokens + stats.total_completion_tokens).toLocaleString()}
              </h3>
            </div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl p-5 border border-gray-200 dark:border-gray-700 shadow-sm flex items-center gap-4">
            <div className="p-3 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded-lg">
               <Clock className="w-5 h-5" />
            </div>
             <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('history.avgDuration', 'Avg Duration')}</p>
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                {statsLoading || !stats ? '-' : `${(stats.avg_duration_ms / 1000).toFixed(2)}s`}
              </h3>
            </div>
          </div>
        </div>

        {/* Filters & List */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden flex flex-col mb-8">
          
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/80 flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('history.details', 'Details')}</h2>
            <div className="flex gap-2">
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <select
                  value={featureFilter}
                  onChange={(e) => setFeatureFilter(e.target.value)}
                  className="pl-9 pr-8 py-1.5 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-700 dark:text-gray-200 appearance-none"
                >
                  <option value="">{t('history.allFeatures', 'All Features')}</option>
                  <option value="chat">Chat</option>
                  <option value="agent">Agent</option>
                  <option value="design">Design</option>
                  <option value="python_agent">Python Agent</option>
                  <option value="ai_edit">AI Edit</option>
                </select>
              </div>

              <div className="relative">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="pl-4 pr-8 py-1.5 text-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-700 dark:text-gray-200 appearance-none"
                >
                  <option value="">{t('history.allStatuses', 'All Statuses')}</option>
                  <option value="success">{t('cell.success', 'Success')}</option>
                  <option value="error">{t('cell.error', 'Error')}</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="px-6 py-3 font-medium">{t('history.time', 'Time')}</th>
                  <th className="px-6 py-3 font-medium">{t('history.feature', 'Feature')}</th>
                  <th className="px-6 py-3 font-medium">{t('history.model', 'Model')}</th>
                  <th className="px-6 py-3 font-medium">{t('history.duration', 'Duration')}</th>
                  <th className="px-6 py-3 font-medium">{t('history.status', 'Status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map(log => (
                  <tr 
                    key={log.id} 
                    onClick={() => openLogDetails(log.id)}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 text-gray-900 dark:text-gray-200">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                        {log.feature}
                      </span>
                      {log.cell_id && <span className="ml-2 text-xs text-gray-400">cell_id: {log.cell_id.substring(0, 6)}...</span>}
                    </td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 max-w-[150px] truncate">
                      {log.model}
                    </td>
                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400">
                      {log.duration_ms / 1000}s
                    </td>
                    <td className="px-6 py-4">
                      {log.status === 'success' ? (
                        <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="w-4 h-4" />
                          <span>{t('cell.success', 'Success')}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                          <XCircle className="w-4 h-4" />
                          <span>{t('cell.error', 'Error')}</span>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {logs.length === 0 && !loading && (
             <div className="p-12 text-center text-gray-500 dark:text-gray-400 flex flex-col items-center justify-center gap-3">
               <Search className="w-10 h-10 text-gray-300 dark:text-gray-600" />
               <p>{t('history.noLogs', 'No history records found')}</p>
             </div>
          )}
          
          {error && (
            <div className="p-12 text-center text-rose-500 flex flex-col items-center justify-center gap-3">
              <AlertCircle className="w-8 h-8" />
              <p>{error}</p>
            </div>
          )}

          {logs.length < total && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-center bg-gray-50 dark:bg-gray-800">
              <button
                onClick={() => fetchLogs(page + 1)}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 disabled:opacity-50"
              >
                {loading ? t('common.loading', 'Loading...') : 'Load More'}
              </button>
            </div>
          )}

        </div>
      </div>

      {/* Log Details Modal */}
      {(selectedLog || detailsLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm"
             onClick={() => setSelectedLog(null)}
        >
          <div 
            className="bg-white dark:bg-gray-800 w-full max-w-4xl max-h-[90vh] rounded-2xl shadow-xl flex flex-col overflow-hidden" 
            onClick={e => e.stopPropagation()}
          >
            {detailsLoading ? (
               <div className="p-12 flex justify-center text-gray-400">
                 {t('common.loading', 'Loading...')}
               </div>
            ) : selectedLog ? (
              <>
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-3">
                    {selectedLog.feature}
                    {selectedLog.status === 'success' ? 
                      <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 px-2 py-0.5 rounded-full">{t('cell.success', 'Success')}</span> : 
                      <span className="text-xs bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-400 px-2 py-0.5 rounded-full">{t('cell.error', 'Error')}</span>
                    }
                  </h3>
                  <button onClick={() => setSelectedLog(null)} className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700">
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {/* Meta */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">{t('history.model', 'Model')}</div>
                      <div className="font-medium text-gray-900 dark:text-white break-all">{selectedLog.model}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">{t('history.duration', 'Duration')}</div>
                      <div className="font-medium text-gray-900 dark:text-white">{selectedLog.duration_ms / 1000}s</div>
                    </div>
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">{t('history.promptTokens', 'Prompt Tokens')}</div>
                      <div className="font-medium text-gray-900 dark:text-white">{selectedLog.tokens_prompt}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">{t('history.completionTokens', 'Completion Tokens')}</div>
                      <div className="font-medium text-gray-900 dark:text-white">{selectedLog.tokens_completion}</div>
                    </div>
                  </div>

                  {selectedLog.error && (
                    <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 p-4 rounded-xl">
                      <h4 className="text-sm font-semibold text-rose-800 dark:text-rose-300 mb-2">{t('history.errorDetails', 'Error Details')}</h4>
                      <pre className="text-xs font-mono text-rose-700 dark:text-rose-400 whitespace-pre-wrap">{selectedLog.error}</pre>
                    </div>
                  )}

                  {/* Messages */}
                  {selectedLog.messages && (
                    <div>
                      <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-3">{t('history.messages', 'Prompt Messages')}</h4>
                      <div className="bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden divide-y divide-gray-200 dark:divide-gray-800">
                        {selectedLog.messages.map((msg: any, i) => (
                          <div key={i} className="p-4 flex flex-col sm:flex-row gap-4">
                            <div className="w-16 flex-shrink-0">
                               <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${msg.role === 'system' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400' : msg.role === 'user' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'}`}>
                                  {msg.role}
                               </span>
                            </div>
                            <pre className="flex-1 text-sm font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap overflow-x-auto">
                              {typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content, null, 2)}
                            </pre>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Response */}
                  {selectedLog.response && (
                    <div>
                       <h4 className="text-md font-semibold text-gray-900 dark:text-white mb-3">{t('history.response', 'Response')}</h4>
                       <div className="bg-gray-800 dark:bg-black rounded-xl p-4 overflow-x-auto">
                          <pre className="text-sm font-mono text-gray-200 whitespace-pre-wrap">
                            {selectedLog.response}
                          </pre>
                       </div>
                    </div>
                  )}
                  
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

    </div>
  );
}
