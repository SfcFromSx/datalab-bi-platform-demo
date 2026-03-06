import { useState } from 'react';
import type { Cell } from '../../types';
import { useNotebookStore } from '../../stores/notebookStore';
import CellToolbar from './CellToolbar';
import CellGenerationPanel from './CellGenerationPanel';
import CellAgentRuntimeCard from './CellAgentRuntimeCard';
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
  const {
    executeCell,
    deleteCell,
    moveCell,
    updateCellSource,
    editCellWithAI,
    clearCellAIState,
    aiEditStateByCellId,
  } = useNotebookStore();
  const aiState = aiEditStateByCellId[cell.id];
  const isEditingAI = aiState?.status === 'generating';

  const handleRun = async () => {
    setIsRunning(true);
    try {
      await executeCell(cell.id, cell.source);
    } finally {
      setIsRunning(false);
    }
  };

  const handleEditAI = async (prompt: string) => {
    await editCellWithAI(cell.id, prompt);
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
    <div className="group overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-900 lg:flex">
      <div className="min-w-0 flex-1">
        <CellToolbar
          cellType={cell.cell_type}
          isRunning={isRunning}
          isEditingAI={isEditingAI}
          aiProgress={aiState?.progress}
          onRun={handleRun}
          onDelete={handleDelete}
          onMoveUp={handleMoveUp}
          onMoveDown={handleMoveDown}
          onEditAI={handleEditAI}
          isFirst={index === 0}
          isLast={index === totalCells - 1}
        />
        {renderCell()}
        {cell.output?.agent && <CellAgentRuntimeCard runtime={cell.output.agent} />}
      </div>
      {aiState && (
        <CellGenerationPanel
          state={aiState}
          onClose={() => clearCellAIState(cell.id)}
        />
      )}
    </div>
  );
}
