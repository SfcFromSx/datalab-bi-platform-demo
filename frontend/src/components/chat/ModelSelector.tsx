import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Check, Loader2, Sparkles } from 'lucide-react';
import { listModels, setActiveModel } from '../../services/api';
import { useModelUIStore } from '../../stores/modelUIStore';
import type { ModelInfo } from '../../types';

interface ModelSelectorProps {
  /** Compact style for header (no full width) */
  compact?: boolean;
}

export default function ModelSelector({ compact }: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [activeId, setActiveId] = useState('');
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listModels()
      .then((data) => {
        setModels(data.models);
        setActiveId(data.active_id);
        const activePreset = data.models.find((m) => m.id === data.active_id);
        useModelUIStore.getState().setActiveModelName(activePreset?.name ?? null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSwitch = async (id: string) => {
    if (id === activeId || switching) return;
    setSwitching(true);
    try {
      const data = await setActiveModel(id);
      setModels(data.models);
      setActiveId(data.active_id);
      const activePreset = data.models.find((m) => m.id === data.active_id);
      useModelUIStore.getState().setActiveModelName(activePreset?.name ?? null);
    } catch {
      // ignore
    }
    setSwitching(false);
    setOpen(false);
  };

  const active = models.find((m) => m.id === activeId);
  const canSwitch = models.length > 1;

  // Always show current model; dropdown only when more than one
  return (
    <div ref={ref} className={`relative ${compact ? 'w-auto' : 'mx-3 mt-1'}`}>
      <button
        type="button"
        onClick={() => canSwitch && setOpen(!open)}
        className={`flex items-center gap-1.5 rounded-md text-[11px] text-gray-500 dark:text-gray-400 transition-colors ${
          compact
            ? 'px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800'
            : 'w-full px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800'
        } ${!canSwitch ? 'cursor-default' : ''}`}
        title={active ? `Model for Chat & AI Edit: ${active.name}` : 'Model'}
      >
        <Sparkles size={11} className="text-purple-500 flex-shrink-0" />
        <span className="truncate max-w-[120px] sm:max-w-[180px]">{active?.name || 'Model'}</span>
        {canSwitch && (
          switching ? (
            <Loader2 size={10} className="flex-shrink-0 animate-spin" />
          ) : (
            <ChevronDown size={10} className={`flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
          )
        )}
      </button>

      {open && canSwitch && (
        <div className="absolute left-0 right-0 top-full mt-1 min-w-[200px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-30 py-1">
          {models.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => handleSwitch(m.id)}
              disabled={switching}
              className={`flex items-center gap-2 w-full px-3 py-1.5 text-xs text-left transition-colors ${
                m.id === activeId
                  ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              {m.id === activeId ? (
                <Check size={12} className="text-blue-500 flex-shrink-0" />
              ) : (
                <span className="w-3 flex-shrink-0" />
              )}
              <div className="min-w-0">
                <div className="font-medium truncate">{m.name}</div>
                <div className="text-[10px] text-gray-400 dark:text-gray-500 truncate">{m.model}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
