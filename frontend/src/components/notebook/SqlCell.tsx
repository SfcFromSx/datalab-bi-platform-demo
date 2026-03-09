import type { Cell } from '../../types';
import MonacoEditor from '../editor/MonacoEditor';
import DataTable from '../common/DataTable';

interface Props {
  cell: Cell;
  onChange: (value: string) => void;
}

export default function SqlCell({ cell, onChange }: Props) {
  const output = cell.output;
  const hasResult = output && (output.columns || output.data);

  return (
    <div>
      <div className="border-b border-gray-100 dark:border-gray-800">
        <MonacoEditor
          value={cell.source}
          onChange={onChange}
          language="sql"
          height="120px"
        />
      </div>

      {output && (
        <details open className="border-t border-gray-100 dark:border-gray-800">
          <summary className="px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
            {output.row_count !== undefined ? `SQL Result (${output.row_count} rows)` : 'SQL Result'}
          </summary>
          <div className="p-3">
            {output.error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-700 dark:text-red-300 text-sm font-mono">
                {output.error}
              </div>
            )}

            {hasResult && (
              <DataTable
                columns={output.columns || output.data?.columns || []}
                rows={output.rows || output.data?.rows || []}
              />
            )}
          </div>
        </details>
      )}
    </div>
  );
}
