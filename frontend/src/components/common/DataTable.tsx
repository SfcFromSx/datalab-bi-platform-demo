import type { ReactNode } from 'react';

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
  maxRows?: number;
}

export default function DataTable({ columns, rows, maxRows = 100 }: DataTableProps) {
  const displayRows = rows.slice(0, maxRows);
  const totalRows = rows.length;
  const isTruncated = totalRows > maxRows;

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
          {totalRows} {totalRows === 1 ? 'row' : 'rows'}
          {isTruncated && ` (showing first ${maxRows})`}
        </span>
        {isTruncated && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">
            {maxRows} max
          </span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              {columns.map((col, i) => (
                <th
                  key={i}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-600 dark:text-gray-300"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
            {displayRows.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={
                  rowIdx % 2 === 1
                    ? 'bg-gray-50/50 dark:bg-gray-700/20'
                    : 'bg-white dark:bg-gray-800'
                }
              >
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className="whitespace-nowrap px-4 py-2 text-sm text-gray-700 dark:text-gray-300"
                  >
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCell(value: unknown): ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-gray-400 dark:text-gray-500">—</span>;
  }
  if (typeof value === 'object' && value !== null && 'toISOString' in value) {
    return String((value as Date).toISOString?.() ?? value);
  }
  return String(value);
}
