import type { Cell } from '../../types';
import MonacoEditor from '../editor/MonacoEditor';
import DataTable from '../common/DataTable';

interface Props {
  cell: Cell;
  onChange: (value: string) => void;
}

export default function PythonCell({ cell, onChange }: Props) {
  const output = cell.output;

  return (
    <div>
      <div className="border-b border-gray-100 dark:border-gray-800">
        <MonacoEditor value={cell.source} onChange={onChange} language="python" height="160px" readOnly={true} />
      </div>
      {output && (
        <details open className="border-t border-gray-100 dark:border-gray-800">
          <summary className="px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
            Python Result
          </summary>
          <div className="p-3 space-y-2">
            {output.error && (
              <pre className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-red-700 dark:text-red-300 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                {output.error}
              </pre>
            )}
            {output.stdout && (
              <pre className="p-3 bg-gray-50 dark:bg-gray-800 rounded text-sm font-mono overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
                {output.stdout}
              </pre>
            )}
            {output.stderr && !output.error && (
              <pre className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded text-sm font-mono overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto text-amber-700 dark:text-amber-300">
                {output.stderr}
              </pre>
            )}
            {output.data && <DataTable columns={output.data.columns} rows={output.data.rows} />}
          </div>
        </details>
      )}
    </div>
  );
}
