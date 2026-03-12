import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Send, X, Bot, User, Loader2, Trash2, Database, CheckCircle2 } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useNotebookStore } from '../../stores/notebookStore';
import { useUIStore } from '../../stores/uiStore';
import ModeSelector from './ModeSelector';
import { ActionStep, ActionResultStep } from './DesignStepRenderer';
import { PlanStep, AgentActionStep, AgentProgressStep, SummaryStep } from './AgentStepRenderer';
import ReactMarkdown from 'react-markdown';
import DataTable from '../common/DataTable';
import ChartRenderer from '../chart/ChartRenderer';
import type { ChatMessage, ChatStep, TableData } from '../../types';

/* ------------------------------------------------------------------ */
/*  Step renderers                                                     */
/* ------------------------------------------------------------------ */

function ThinkingStep({ step }: { step: ChatStep }) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 italic py-1">
      {step.streaming && <Loader2 size={12} className="animate-spin" />}
      <span>{step.content as string}</span>
    </div>
  );
}

function SqlStep({ step }: { step: ChatStep }) {
  return (
    <div className="my-2">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
        <Database size={11} />
        <span>SQL</span>
        {step.streaming && <Loader2 size={10} className="animate-spin ml-1" />}
      </div>
      <pre className="text-[11px] leading-relaxed font-mono bg-gray-50 dark:bg-gray-800/60 p-3 rounded-lg border border-gray-200 dark:border-gray-700 text-purple-600 dark:text-purple-400 overflow-x-auto whitespace-pre-wrap">
        <code>{step.content as string}</code>
      </pre>
    </div>
  );
}

function ExecutingStep({ step }: { step: ChatStep }) {
  return (
    <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 py-1">
      {step.streaming ? (
        <Loader2 size={12} className="animate-spin" />
      ) : (
        <CheckCircle2 size={12} className="text-green-500" />
      )}
      <span>Running query...</span>
    </div>
  );
}

function DataStep({ step }: { step: ChatStep }) {
  const data = step.content as TableData;
  if (!data?.columns?.length) return null;
  return (
    <div className="my-2">
      <DataTable columns={data.columns} rows={data.rows} maxRows={20} />
    </div>
  );
}

function ChartStep({ step }: { step: ChatStep }) {
  const option = step.content as Record<string, unknown>;
  if (!option || typeof option !== 'object') return null;
  return (
    <div className="my-2 bg-white dark:bg-gray-900 p-2 rounded-lg border border-gray-200 dark:border-gray-700">
      <ChartRenderer option={option as any} height="280px" />
    </div>
  );
}

function AnswerStep({ step }: { step: ChatStep }) {
  return (
    <div className="text-sm text-gray-700 dark:text-gray-200 pt-1">
      <ReactMarkdown>{step.content as string}</ReactMarkdown>
    </div>
  );
}

function ErrorStep({ step }: { step: ChatStep }) {
  return (
    <div className="my-1 px-3 py-2 text-xs bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
      {step.content as string}
    </div>
  );
}

function StepRenderer({ step }: { step: ChatStep }) {
  switch (step.type) {
    case 'thinking':
      return <ThinkingStep step={step} />;
    case 'sql':
      return <SqlStep step={step} />;
    case 'executing':
      return <ExecutingStep step={step} />;
    case 'data':
      return <DataStep step={step} />;
    case 'chart':
      return <ChartStep step={step} />;
    case 'answer':
      return <AnswerStep step={step} />;
    case 'error':
      return <ErrorStep step={step} />;
    case 'action':
      return <ActionStep step={step} />;
    case 'action_result':
      return <ActionResultStep step={step} />;
    case 'plan':
      return <PlanStep step={step} />;
    case 'agent_action':
      return <AgentActionStep step={step} />;
    case 'agent_progress':
      return <AgentProgressStep step={step} />;
    case 'summary':
      return <SummaryStep step={step} />;
    default:
      return null;
  }
}

/* ------------------------------------------------------------------ */
/*  Message bubble                                                     */
/* ------------------------------------------------------------------ */

function MessageBubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === 'user') {
    return (
      <div className="flex gap-2 justify-end">
        <div className="max-w-[85%] px-3 py-2 rounded-lg rounded-br-sm bg-blue-500 text-white text-sm">
          {msg.content}
        </div>
        <div className="w-7 h-7 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center flex-shrink-0">
          <User size={14} className="text-white" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2 justify-start">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
        <Bot size={14} className="text-white" />
      </div>
      <div className={`px-3 py-2 rounded-lg rounded-bl-sm bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 overflow-x-auto ${msg.steps.length > 0 ? "w-full max-w-full" : "max-w-[85%]"}`}>
        {msg.steps.length > 0 ? (
          <div className="space-y-1">
            {msg.steps.map((step, i) => (
              <StepRenderer key={i} step={step} />
            ))}
          </div>
        ) : msg.status === 'streaming' ? (
          <Loader2 size={16} className="animate-spin text-blue-500" />
        ) : (
          <ReactMarkdown className="text-sm">{msg.content}</ReactMarkdown>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Placeholder text per mode                                          */
/* ------------------------------------------------------------------ */

const PLACEHOLDERS: Record<string, string> = {
  chat: 'chat.placeholder',
  design: 'chat.placeholder.design',
  agent: 'chat.placeholder.agent',
};

/* ------------------------------------------------------------------ */
/*  Chat panel                                                         */
/* ------------------------------------------------------------------ */

export default function ChatPanel() {
  const { t } = useTranslation();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isLoading, sendQuery, sendDesignQuery, sendAgentTask, clearHistory, getMessages } = useChatStore();
  const { activeNotebook } = useNotebookStore();
  const { chatOpen, toggleChat, chatMode, setChatMode } = useUIStore();

  const messages = getMessages(chatMode);

  const [width, setWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const resizerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = document.body.clientWidth - e.clientX;
      if (newWidth >= 320 && newWidth <= 800) setWidth(newWidth);
    };
    const handleMouseUp = () => setIsResizing(false);

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const query = input.trim();
    setInput('');

    switch (chatMode) {
      case 'chat':
        await sendQuery(query, activeNotebook?.id);
        break;
      case 'design':
        if (activeNotebook) {
          await sendDesignQuery(query, activeNotebook.id);
        }
        break;
      case 'agent':
        await sendAgentTask(query, activeNotebook?.id);
        break;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!chatOpen) return null;

  const designNeedsNotebook = chatMode === 'design' && !activeNotebook;

  return (
    <div
      className="relative flex flex-col bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 z-10"
      style={{ width: `${width}px` }}
    >
      {/* Resize handle */}
      <div
        ref={resizerRef}
        onMouseDown={() => setIsResizing(true)}
        className="absolute left-0 top-0 bottom-0 w-1 bg-transparent hover:bg-blue-500 cursor-col-resize z-20 group"
      >
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-8 bg-gray-300 dark:bg-gray-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
        <div className="flex items-center gap-2">
          <Bot size={18} />
          <span className="font-semibold text-sm">{t('chat.title')}</span>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={() => clearHistory(chatMode)}
              className="p-1 text-white/80 hover:text-white hover:bg-white/10 rounded transition-colors"
              title={t('chat.clearHistory', 'Clear History')}
            >
              <Trash2 size={16} />
            </button>
          )}
          <button
            onClick={toggleChat}
            className="p-1 text-white/80 hover:text-white hover:bg-white/10 rounded transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Mode selector */}
      <ModeSelector value={chatMode} onChange={setChatMode} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Bot size={32} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-500">{t(`chat.welcome.${chatMode}`, t('chat.welcome'))}</p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-700">
        {designNeedsNotebook && (
          <div className="text-xs text-amber-600 dark:text-amber-400 mb-2 px-1">
            {t('chat.designNeedsNotebook', 'Open a notebook to use Design mode')}
          </div>
        )}
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t(PLACEHOLDERS[chatMode] ?? 'chat.placeholder')}
            disabled={isLoading || designNeedsNotebook}
            className="flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || designNeedsNotebook}
            className="p-2 rounded-lg bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
