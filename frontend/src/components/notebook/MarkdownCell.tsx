import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Cell } from '../../types';
import MonacoEditor from '../editor/MonacoEditor';

interface Props {
  cell: Cell;
  onChange: (value: string) => void;
}

export default function MarkdownCell({ cell, onChange }: Props) {
  const [editing, setEditing] = useState(!cell.source);

  if (editing) {
    return (
      <div>
        <MonacoEditor value={cell.source} onChange={onChange} language="markdown" height="150px" />
        <div className="px-3 py-1.5 border-t border-gray-100 dark:border-gray-800">
          <button onClick={() => setEditing(false)} className="text-xs text-blue-500 hover:text-blue-600">Preview</button>
        </div>
      </div>
    );
  }

  return (
    <div onDoubleClick={() => setEditing(true)} className="p-4 prose dark:prose-invert prose-sm max-w-none cursor-text min-h-[60px]">
      {cell.source ? (
        <ReactMarkdown>{(cell.output as any)?.html || cell.source}</ReactMarkdown>
      ) : (
        <p className="text-gray-400 italic">Double-click to edit...</p>
      )}
    </div>
  );
}
