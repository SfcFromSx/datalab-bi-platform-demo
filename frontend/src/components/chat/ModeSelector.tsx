import { useTranslation } from 'react-i18next';
import { MessageCircle, PenTool, Cpu } from 'lucide-react';
import type { ChatMode } from '../../types';

const MODES: { id: ChatMode; icon: typeof MessageCircle; labelKey: string }[] = [
  { id: 'chat', icon: MessageCircle, labelKey: 'chat.mode.chat' },
  { id: 'design', icon: PenTool, labelKey: 'chat.mode.design' },
  { id: 'agent', icon: Cpu, labelKey: 'chat.mode.agent' },
];

interface ModeSelectorProps {
  value: ChatMode;
  onChange: (mode: ChatMode) => void;
}

export default function ModeSelector({ value, onChange }: ModeSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-0.5 mx-3 mt-2 mb-1">
      {MODES.map(({ id, icon: Icon, labelKey }) => {
        const active = value === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-xs font-medium transition-all ${
              active
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <Icon size={13} />
            <span>{t(labelKey)}</span>
          </button>
        );
      })}
    </div>
  );
}
