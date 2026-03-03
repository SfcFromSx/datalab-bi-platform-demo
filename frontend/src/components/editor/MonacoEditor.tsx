import Editor from '@monaco-editor/react';
import { useMemo } from 'react';
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

  return (
    <Editor
      height={height}
      language={language}
      value={value}
      onChange={(v) => onChange(v ?? '')}
      theme={theme}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        wordWrap: 'on',
      }}
    />
  );
}
