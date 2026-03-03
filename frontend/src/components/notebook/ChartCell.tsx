import { useMemo } from 'react';
import type { Cell } from '../../types';
import ChartRenderer from '../chart/ChartRenderer';
import MonacoEditor from '../editor/MonacoEditor';

interface Props {
  cell: Cell;
  onChange: (value: string) => void;
}

export default function ChartCell({ cell, onChange }: Props) {
  const chartOption = useMemo(() => {
    try { return JSON.parse(cell.source); } catch { return null; }
  }, [cell.source]);

  return (
    <div>
      {chartOption ? (
        <div className="p-4"><ChartRenderer option={chartOption} height="350px" /></div>
      ) : (
        <div className="p-2 text-sm text-gray-500 dark:text-gray-400">Enter a valid ECharts JSON specification below:</div>
      )}
      <details className="border-t border-gray-100 dark:border-gray-800">
        <summary className="px-3 py-2 text-xs text-gray-500 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
          Chart Specification (JSON)
        </summary>
        <MonacoEditor value={cell.source} onChange={onChange} language="json" height="200px" />
      </details>
    </div>
  );
}
