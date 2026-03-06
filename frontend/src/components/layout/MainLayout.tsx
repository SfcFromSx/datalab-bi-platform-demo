import { useEffect, useState } from 'react';
import { MessageSquare } from 'lucide-react';
import Header from '../common/Header';
import Sidebar from '../sidebar/Sidebar';
import Notebook from '../notebook/Notebook';
import ChatPanel from '../chat/ChatPanel';
import { useUIStore } from '../../stores/uiStore';
import { useNotebookStore } from '../../stores/notebookStore';

export default function MainLayout() {
  const { sidebarOpen, chatOpen, toggleChat } = useUIStore();
  const [selectedNotebookId, setSelectedNotebookId] = useState<string | null>(null);

  const handleSelectNotebook = (id: string | null) => {
    setSelectedNotebookId(id);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-950">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {sidebarOpen && (
          <Sidebar
            onSelectNotebook={handleSelectNotebook}
            activeNotebookId={selectedNotebookId || undefined}
          />
        )}

        <main className="flex-1 overflow-y-auto">
          {selectedNotebookId ? (
            <Notebook notebookId={selectedNotebookId} />
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-4">
                <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-emerald-500 via-cyan-500 to-slate-900 flex items-center justify-center shadow-lg">
                  <span className="text-3xl font-bold text-white">D</span>
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  Welcome to DataLab
                </h2>
                <p className="text-gray-500 max-w-md">
                  Select a notebook from the sidebar or create a new one to get started with LLM-powered business intelligence.
                </p>
              </div>
            </div>
          )}
        </main>

        <ChatPanel />
      </div>

      {!chatOpen && (
        <button
          onClick={toggleChat}
          className="fixed bottom-4 right-4 w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-lg hover:shadow-xl flex items-center justify-center transition-all hover:scale-105 z-40"
          title="AI Assistant"
        >
          <MessageSquare size={20} />
        </button>
      )}
    </div>
  );
}
