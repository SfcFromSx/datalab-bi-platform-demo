import { useMemo } from 'react';
import type { Cell } from '../../types';
import ChartRenderer from '../chart/ChartRenderer';
import MonacoEditor from '../editor/MonacoEditor';
import { useNotebookStore } from '../../stores/notebookStore';

interface Props {
  cell: Cell;
  onChange: (value: string) => void;
}

export default function ChartCell({ cell, onChange }: Props) {
  const cells = useNotebookStore((state) => state.cells);

  const chartState = useMemo(() => {
    try { return JSON.parse(cell.source); } catch { return null; }
  }, [cell.source]);

  const chartOption = useMemo(() => {
    if (!chartState) {
      return null;
    }
    return resolveNotebookChartOption(chartState, cells);
  }, [cells, chartState]);

  const chartError = useMemo(() => {
    if (!chartState) {
      return 'Enter a valid JSON chart specification below.';
    }
    const dataSource = chartState.data_source;
    if (typeof dataSource === 'string' && dataSource && !findNotebookTable(cells, dataSource)) {
      return `Notebook data source "${dataSource}" was not found in prior cell outputs.`;
    }
    return null;
  }, [cells, chartState]);

  return (
    <div>
      {chartOption ? (
        <div className="p-4"><ChartRenderer option={chartOption} height="350px" /></div>
      ) : (
        <div className="p-2 text-sm text-gray-500 dark:text-gray-400">{chartError}</div>
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

function resolveNotebookChartOption(
  spec: Record<string, unknown>,
  cells: Cell[],
) {
  const dataSource = typeof spec.data_source === 'string' ? spec.data_source : null;
  const table = dataSource ? findNotebookTable(cells, dataSource) : null;
  if (!table) {
    return spec;
  }

  const chartType =
    typeof spec.chart_type === 'string'
      ? spec.chart_type
      : typeof spec.type === 'string'
        ? spec.type
        : Array.isArray(spec.series) && spec.series[0] && typeof spec.series[0] === 'object' && spec.series[0] !== null && 'type' in spec.series[0]
          ? String((spec.series[0] as { type?: unknown }).type ?? 'bar')
          : 'bar';

  const xField =
    typeof spec.x_field === 'string' && spec.x_field
      ? spec.x_field
      : table.columns[0];
  const requestedYField = spec.y_field;
  const yFields = Array.isArray(requestedYField)
    ? requestedYField.filter((field): field is string => typeof field === 'string')
    : typeof requestedYField === 'string'
      ? [requestedYField]
      : table.columns.slice(1, 2);

  const dataset = {
    ...(typeof spec.dataset === 'object' && spec.dataset ? spec.dataset : {}),
    source: [table.columns, ...table.rows],
  };

  if (Array.isArray(spec.series) && spec.series.length > 0) {
    return {
      ...spec,
      dataset,
      xAxis: spec.xAxis ?? { type: 'category' },
      yAxis: spec.yAxis ?? { type: 'value' },
      series: spec.series.map((series, index) => {
        if (!series || typeof series !== 'object') {
          return series;
        }
        const existingSeries = series as Record<string, unknown>;
        if ('data' in existingSeries || 'encode' in existingSeries) {
          return existingSeries;
        }
        return {
          ...existingSeries,
          type: typeof existingSeries.type === 'string' ? existingSeries.type : chartType,
          encode: {
            x: xField,
            y: yFields[index] ?? yFields[0],
          },
        };
      }),
    };
  }

  if (chartType === 'pie') {
    return {
      ...spec,
      dataset,
      tooltip: spec.tooltip ?? { trigger: 'item' },
      series: [
        {
          type: 'pie',
          encode: {
            itemName: xField,
            value: yFields[0],
          },
        },
      ],
    };
  }

  return {
    ...spec,
    dataset,
    tooltip: spec.tooltip ?? { trigger: 'axis' },
    xAxis: spec.xAxis ?? { type: 'category' },
    yAxis: spec.yAxis ?? { type: 'value' },
    series: yFields.map((field) => ({
      type: chartType,
      name: field,
      encode: {
        x: xField,
        y: field,
      },
    })),
  };
}

function findNotebookTable(cells: Cell[], variableName: string) {
  for (const notebookCell of cells) {
    const output = notebookCell.output;
    if (!output) {
      continue;
    }

    if (output.data?.variable === variableName) {
      return {
        columns: output.data.columns,
        rows: output.data.rows,
      };
    }

    if (output.columns && output.rows) {
      const match = notebookCell.source.match(/--\s*output:\s*(\w+)/i);
      if (match?.[1] === variableName) {
        return {
          columns: output.columns,
          rows: output.rows,
        };
      }
    }
  }
  return null;
}
