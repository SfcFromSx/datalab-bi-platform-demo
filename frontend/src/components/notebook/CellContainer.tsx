import { useState } from 'react';
import type { Cell } from '../../types';
import { useNotebookStore } from '../../stores/notebookStore';
import CellToolbar from './CellToolbar';
import SqlCell from './SqlCell';
import PythonCell from './PythonCell';
import ChartCell from './ChartCell';
import MarkdownCell from './MarkdownCell';

interface Props {
  cell: Cell;
  index: number;
  totalCells: number;
}

export default function CellContainer({ cell, index, totalCells }: Props) {
  const [isRunning, setIsRunning] = useState(false);
  const { executeCell, deleteCell, moveCell, updateCellSource } = useNotebookStore();

  const handleRun = async () => {
    setIsRunning(true);
    try {
      await executeCell(cell.id, cell.source);
    } finally {
      setIsRunning(false);
    }
  };

  const handleDelete = () => deleteCell(cell.id);
  const handleMoveUp = () => index > 0 && moveCell(cell.id, cell.position - 1);
  const handleMoveDown = () => index < totalCells - 1 && moveCell(cell.id, cell.position + 1);
  const handleSourceChange = (value: string) => updateCellSource(cell.id, value);

  const renderCell = () => {
    switch (cell.cell_type) {
      case 'sql':
        return <SqlCell cell={cell} onChange={handleSourceChange} />;
      case 'python':
        return <PythonCell cell={cell} onChange={handleSourceChange} />;
      case 'chart':
        return <ChartCell cell={cell} onChange={handleSourceChange} />;
      case 'markdown':
        return <MarkdownCell cell={cell} onChange={handleSourceChange} />;
      default:
        return <div className="p-4 text-gray-500">Unknown cell type</div>;
    }
  };

  return (
    <div className="group border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900 shadow-sm hover:shadow-md transition-shadow">
      <CellToolbar
        cellType={cell.cell_type}
        isRunning={isRunning}
        onRun={handleRun}
        onDelete={handleDelete}
        onMoveUp={handleMoveUp}
        onMoveDown={handleMoveDown}
        isFirst={index === 0}
        isLast={index === totalCells - 1}
      />
      {renderCell()}
    </div>
  );
}
