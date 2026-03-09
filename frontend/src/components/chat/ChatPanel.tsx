import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, X, Bot, User, Loader2, Trash2, ChevronDown, ChevronRight, CheckCircle2, AlertCircle } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useNotebookStore } from '../../stores/notebookStore';
import { useUIStore } from '../../stores/uiStore';
import ReactMarkdown from 'react-markdown';
import DataTable from '../common/DataTable';
import ChartRenderer from '../chart/ChartRenderer';
import type { ChatSection } from '../../types';

function MessageSection({ section }: { section: ChatSection }) {
  const [isOpen, setIsOpen] = useState(section.status === 'running');

  // Auto-expand if it changes to running
  useEffect(() => {
    if (section.status === 'running') {
      setIsOpen(true);
    }
  }, [section.status]);

  const getIcon = () => {
    if (section.status === 'running') return <Loader2 size={14} className="animate-spin text-blue-500" />;
    if (section.status === 'error') return <AlertCircle size={14} className="text-red-500" />;
    return <CheckCircle2 size={14} className="text-green-500" />;
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden mb-2 last:mb-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-2 py-1.5 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-xs font-medium text-gray-600 dark:text-gray-300"
      >
        <div className="flex items-center gap-2">
          {getIcon()}
          <span>{section.title}</span>
        </div>
        {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {isOpen && (
        <div className="p-2 bg-white dark:bg-gray-900 overflow-x-auto">
          {section.type === 'sql' ? (
            <pre className="text-[10px] leading-relaxed font-mono bg-gray-50 dark:bg-gray-800/50 p-2 rounded border border-gray-100 dark:border-gray-800 text-purple-600 dark:text-purple-400">
              <code>{section.content}</code>
            </pre>
          ) : (
            <ReactMarkdown className="markdown-body text-xs">{section.content}</ReactMarkdown>
          )}
        </div>
      )}
    </div>
  );
}

export default function ChatPanel() {
  const { t } = useTranslation();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, sendQuery, clearHistory } = useChatStore();
  const { activeNotebook, loadNotebook } = useNotebookStore();
  const { chatOpen, toggleChat } = useUIStore();

  const [width, setWidth] = useState(384); // Default w-96 = 384px
  const [isResizing, setIsResizing] = useState(false);
  const resizerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      // Calculate new width: Screen width minus mouse X position since it's anchored to the right
      const newWidth = document.body.clientWidth - e.clientX;
      if (newWidth >= 300 && newWidth <= 800) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isResizing]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || !activeNotebook || isLoading) return;
    const query = input.trim();
    setInput('');
    await sendQuery(query, activeNotebook.id);
    await loadNotebook(activeNotebook.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!chatOpen) return null;

  return (
    <div
      className="relative flex flex-col bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 z-10 transition-colors"
      style={{ width: `${width}px` }}
    >
      {/* Resizer Handle */}
      <div
        ref={resizerRef}
        onMouseDown={() => setIsResizing(true)}
        className="absolute left-0 top-0 bottom-0 w-1 bg-transparent hover:bg-blue-500 cursor-col-resize z-20 group"
      >
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-8 bg-gray-300 dark:bg-gray-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-500 to-purple-600 rounded-tl-xl text-white">
        <div className="flex items-center gap-2">
          <Bot size={18} />
          <span className="font-semibold text-sm">{t('chat.title')}</span>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="p-1 text-white/80 hover:text-white hover:bg-white/10 rounded transition-colors"
              title={t('chat.clearHistory', 'Clear History')}
            >
              <Trash2 size={16} />
            </button>
          )}
          <button onClick={toggleChat} className="p-1 text-white/80 hover:text-white hover:bg-white/10 rounded transition-colors">
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot size={32} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-500">{t('chat.welcome')}</p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role !== 'user' && (
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <Bot size={14} className="text-white" />
              </div>
            )}
            <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm markdown-body overflow-x-auto break-words ${msg.role === 'user' ? 'bg-blue-500 text-white rounded-br-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-sm [&_table]:w-full [&_table]:text-xs [&_table]:mt-2 [&_th]:bg-gray-200 [&_th]:dark:bg-gray-700 [&_td]:border [&_th]:border [&_td]:border-gray-300 [&_th]:border-gray-300 [&_td]:dark:border-gray-600 [&_th]:dark:border-gray-600 [&_th]:p-1 [&_td]:p-1'}`}>
              {msg.sections && msg.sections.length > 0 ? (
                <div className="space-y-2">
                  {msg.sections.map((section) => (
                    <MessageSection key={section.id} section={section} />
                  ))}
                  {/* Final answer content after sections, if any */}
                  {msg.data || msg.chart ? (
                    <div className="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  ) : null}
                </div>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              )}

              {msg.data && (
                <div className="mt-3">
                  <DataTable columns={msg.data.columns} rows={msg.data.rows} maxRows={10} />
                </div>
              )}

              {msg.chart && (
                <div className="mt-3 bg-white dark:bg-gray-900 p-2 rounded-lg border border-gray-200 dark:border-gray-700">
                  <ChartRenderer option={msg.chart} height="300px" />
                </div>
              )}

              {msg.cells_created && msg.cells_created.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs opacity-75">
                  Created {msg.cells_created.length} cell(s)
                </div>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center flex-shrink-0">
                <User size={14} className="text-white" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
              <Bot size={14} className="text-white" />
            </div>
            <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg rounded-bl-sm">
              <Loader2 size={16} className="animate-spin text-blue-500" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('chat.placeholder')}
            disabled={isLoading || !activeNotebook}
            className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !activeNotebook}
            className="p-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
