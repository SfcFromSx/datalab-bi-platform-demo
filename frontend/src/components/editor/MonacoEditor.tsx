import Editor from '@monaco-editor/react';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useUIStore } from '../../stores/uiStore';

type EditorLanguage = 'sql' | 'python' | 'json' | 'markdown';

interface MonacoEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: EditorLanguage;
  height?: string;
  readOnly?: boolean;
}

export default function MonacoEditor({
  value,
  onChange,
  language = 'sql',
  height = '200px',
  readOnly = false,
}: MonacoEditorProps) {
  const darkMode = useUIStore((s) => s.darkMode);
  const theme = useMemo(() => (darkMode ? 'vs-dark' : 'light'), [darkMode]);
  const initialPx = parseInt(height, 10) || 200;
  const [editorHeight, setEditorHeight] = useState(initialPx);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startH = useRef(0);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    dragging.current = true;
    startY.current = e.clientY;
    startH.current = editorHeight;
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    const delta = e.clientY - startY.current;
    const newH = Math.max(60, Math.min(1200, startH.current + delta));
    setEditorHeight(newH);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    dragging.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <Editor
        height={`${editorHeight}px`}
        language={language}
        value={value}
        onChange={(v) => onChange(v ?? '')}
        theme={theme}
        options={{
          readOnly,
          domReadOnly: readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          cursorStyle: readOnly ? 'underline-thin' : 'line',
        }}
      />
      {/* Drag-to-resize handle */}
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        style={{
          height: '6px',
          cursor: 'row-resize',
          background: 'transparent',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'background 0.15s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = darkMode ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
        title="Drag to resize"
      >
        <div style={{
          width: '36px',
          height: '3px',
          borderRadius: '2px',
          background: darkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)',
        }} />
      </div>
    </div>
  );
}
