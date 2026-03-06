import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Database,
  Folder as FolderIcon,
  FolderOpen,
  FolderPlus,
  GripVertical,
  Plus,
  ShieldCheck,
  Trash2,
  Upload,
} from 'lucide-react';
import { useNotebookStore } from '../../stores/notebookStore';
import { listDataSources, uploadCSV } from '../../services/api';
import type { DataSource, NotebookListItem, Folder } from '../../types';
import { useEnterpriseStore } from '../../stores/enterpriseStore';
import AuditPanel from './AuditPanel';

interface Props {
  onSelectNotebook: (id: string | null) => void;
  activeNotebookId?: string;
}

export default function Sidebar({ onSelectNotebook, activeNotebookId }: Props) {
  const { t } = useTranslation();
  const {
    notebooks, folders,
    fetchNotebooks, fetchFolders,
    createNotebook, deleteNotebook, renameNotebook,
    createFolder, renameFolder, removeFolder, moveToFolder,
  } = useNotebookStore();
  const {
    context,
    workspaceKey,
    auditEvents,
    auditLoading,
    refreshAudit,
  } = useEnterpriseStore();
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [activeTab, setActiveTab] = useState<'notebooks' | 'data' | 'audit'>('notebooks');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editFolderValue, setEditFolderValue] = useState('');
  const [collapsedFolders, setCollapsedFolders] = useState<Set<string>>(new Set());
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null);
  const [dragOverUncategorized, setDragOverUncategorized] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const editFolderInputRef = useRef<HTMLInputElement>(null);

  const canViewAudit = ['owner', 'admin'].includes(context?.workspace.role ?? '');

  useEffect(() => {
    fetchNotebooks();
    fetchFolders();
    listDataSources().then(setDataSources).catch(() => { });
    if (canViewAudit) {
      void refreshAudit();
    }
  }, [canViewAudit, fetchFolders, fetchNotebooks, refreshAudit, workspaceKey]);

  useEffect(() => {
    if (!canViewAudit && activeTab === 'audit') {
      setActiveTab('notebooks');
    }
  }, [activeTab, canViewAudit]);

  useEffect(() => {
    if (editingId && editInputRef.current) {
      editInputRef.current.focus();
      editInputRef.current.select();
    }
  }, [editingId]);

  useEffect(() => {
    if (editingFolderId && editFolderInputRef.current) {
      editFolderInputRef.current.focus();
      editFolderInputRef.current.select();
    }
  }, [editingFolderId]);

  // Group notebooks by folder
  const { uncategorized, folderGroups } = useMemo(() => {
    const uncategorized = notebooks.filter((nb) => !nb.folder_id);
    const folderGroups = new Map<string, NotebookListItem[]>();
    for (const f of folders) {
      folderGroups.set(f.id, []);
    }
    for (const nb of notebooks) {
      if (nb.folder_id && folderGroups.has(nb.folder_id)) {
        folderGroups.get(nb.folder_id)!.push(nb);
      }
    }
    return { uncategorized, folderGroups };
  }, [notebooks, folders]);

  // --- Notebook handlers ---
  const handleCreateNotebook = async (folderId?: string) => {
    const nb = await createNotebook(undefined, undefined, folderId);
    if (nb) {
      onSelectNotebook(nb.id);
      // Auto-expand the folder if creating inside one
      if (folderId) {
        setCollapsedFolders((prev) => {
          const next = new Set(prev);
          next.delete(folderId);
          return next;
        });
      }
    }
  };

  const handleDeleteNotebook = async (e: React.MouseEvent, nbId: string) => {
    e.stopPropagation();
    if (!window.confirm(t('notebook.deleteConfirm'))) return;
    await deleteNotebook(nbId);
    if (nbId === activeNotebookId) onSelectNotebook(null);
  };

  const startRename = (e: React.MouseEvent, nb: NotebookListItem) => {
    e.stopPropagation();
    setEditingId(nb.id);
    setEditValue(nb.title);
  };

  const commitRename = async () => {
    if (editingId && editValue.trim()) await renameNotebook(editingId, editValue.trim());
    setEditingId(null);
  };

  // --- Folder handlers ---
  const startFolderRename = (e: React.MouseEvent, folder: Folder) => {
    e.stopPropagation();
    setEditingFolderId(folder.id);
    setEditFolderValue(folder.name);
  };

  const commitFolderRename = async () => {
    if (editingFolderId && editFolderValue.trim()) await renameFolder(editingFolderId, editFolderValue.trim());
    setEditingFolderId(null);
  };

  const handleDeleteFolder = async (e: React.MouseEvent, folderId: string) => {
    e.stopPropagation();
    if (!window.confirm(t('folder.deleteConfirm'))) return;
    await removeFolder(folderId);
  };

  const toggleFolder = (folderId: string) => {
    setCollapsedFolders((prev) => {
      const next = new Set(prev);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  const handleCreateFolder = async () => {
    const folder = await createFolder();
    if (folder) {
      setEditingFolderId(folder.id);
      setEditFolderValue(folder.name);
    }
  };

  // --- Drag & Drop ---
  const handleDragStart = useCallback((e: React.DragEvent, nbId: string) => {
    e.dataTransfer.setData('text/plain', nbId);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOverFolder = useCallback((e: React.DragEvent, folderId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverFolderId(folderId);
  }, []);

  const handleDragOverUncategorized = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverUncategorized(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOverFolderId(null);
    setDragOverUncategorized(false);
  }, []);

  const handleDropOnFolder = useCallback(async (e: React.DragEvent, folderId: string) => {
    e.preventDefault();
    setDragOverFolderId(null);
    const nbId = e.dataTransfer.getData('text/plain');
    if (nbId) {
      await moveToFolder(nbId, folderId);
      // Auto-expand the target folder
      setCollapsedFolders((prev) => {
        const next = new Set(prev);
        next.delete(folderId);
        return next;
      });
    }
  }, [moveToFolder]);

  const handleDropOnUncategorized = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOverUncategorized(false);
    const nbId = e.dataTransfer.getData('text/plain');
    if (nbId) {
      await moveToFolder(nbId, null);
    }
  }, [moveToFolder]);

  // --- CSV Upload ---
  const handleUploadCSV = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const ds = await uploadCSV(file);
      setDataSources((prev) => [...prev, ds]);
    } catch (err) {
      console.error('Upload failed:', err);
    }
    e.target.value = '';
  };

  // --- Render notebook item ---
  const renderNotebookItem = (nb: NotebookListItem, indent = false) => (
    <div
      key={nb.id}
      draggable={editingId !== nb.id}
      onDragStart={(e) => handleDragStart(e, nb.id)}
      onClick={() => editingId !== nb.id && onSelectNotebook(nb.id)}
      className={`group w-full text-left ${indent ? 'pl-7 pr-3' : 'px-3'} py-2 rounded-md text-sm transition-colors cursor-pointer flex items-center gap-2 ${nb.id === activeNotebookId ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
    >
      {/* Drag handle */}
      <span className="opacity-0 group-hover:opacity-40 cursor-grab flex-shrink-0" title="Drag to move">
        <GripVertical size={12} />
      </span>

      <div className="flex-1 min-w-0">
        {editingId === nb.id ? (
          <input
            ref={editInputRef}
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') setEditingId(null);
            }}
            className="w-full px-1 py-0 text-sm bg-white dark:bg-gray-800 border border-blue-400 rounded outline-none"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <div className="truncate" onDoubleClick={(e) => startRename(e, nb)}>{nb.title}</div>
        )}
        <div className="text-xs text-gray-400 mt-0.5">{nb.cell_count} cells</div>
      </div>

      {editingId !== nb.id && (
        <button
          onClick={(e) => handleDeleteNotebook(e, nb.id)}
          className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 transition-all opacity-0 group-hover:opacity-100 flex-shrink-0"
          title={t('common.delete')}
        >
          <Trash2 size={14} />
        </button>
      )}
    </div>
  );

  return (
    <div className="w-64 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      <div className="m-2 rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-cyan-50 p-3 shadow-sm dark:border-emerald-900/40 dark:from-emerald-950/40 dark:via-gray-900 dark:to-cyan-950/20">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300">
            <ShieldCheck size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
              {t('enterprise.workspace')}
            </p>
            <p className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
              {context?.workspace.name ?? t('common.loading')}
            </p>
            <p className="mt-1 max-h-10 overflow-hidden text-xs text-gray-500 dark:text-gray-400">
              {context?.workspace.description ?? t('enterprise.workspaceDescription')}
            </p>
          </div>
        </div>
      </div>

      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setActiveTab('notebooks')}
          className={`flex-1 px-3 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'notebooks' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          <BookOpen size={14} /> {t('sidebar.notebooks')}
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={`flex-1 px-3 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'data' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
        >
          <Database size={14} /> {t('sidebar.dataSources')}
        </button>
        {canViewAudit && (
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex-1 px-3 py-2.5 text-xs font-medium flex items-center justify-center gap-1.5 transition-colors ${activeTab === 'audit' ? 'text-emerald-600 border-b-2 border-emerald-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            <ShieldCheck size={14} /> {t('enterprise.audit')}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {activeTab === 'notebooks' && (
          <div className="space-y-1">
            {/* Top action bar */}
            <div className="flex items-center gap-1">
              <button onClick={() => handleCreateNotebook()} className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
                <Plus size={14} /> {t('notebook.newNotebook')}
              </button>
              <button onClick={handleCreateFolder} className="p-2 rounded-md text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors" title={t('folder.newFolder')}>
                <FolderPlus size={14} />
              </button>
            </div>

            {/* Folders */}
            {folders.map((folder) => {
              const isCollapsed = collapsedFolders.has(folder.id);
              const folderNbs = folderGroups.get(folder.id) || [];
              const isDragOver = dragOverFolderId === folder.id;
              return (
                <div
                  key={folder.id}
                  onDragOver={(e) => handleDragOverFolder(e, folder.id)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDropOnFolder(e, folder.id)}
                >
                  <div
                    onClick={() => toggleFolder(folder.id)}
                    className={`group flex items-center gap-1 px-2 py-1.5 rounded-md text-sm cursor-pointer transition-colors ${isDragOver ? 'bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-400' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                  >
                    {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
                    {isCollapsed ? <FolderIcon size={14} className="text-amber-500" /> : <FolderOpen size={14} className="text-amber-500" />}
                    {editingFolderId === folder.id ? (
                      <input
                        ref={editFolderInputRef}
                        value={editFolderValue}
                        onChange={(e) => setEditFolderValue(e.target.value)}
                        onBlur={commitFolderRename}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') commitFolderRename();
                          if (e.key === 'Escape') setEditingFolderId(null);
                        }}
                        className="flex-1 px-1 py-0 text-sm bg-white dark:bg-gray-800 border border-blue-400 rounded outline-none"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <span className="flex-1 truncate font-medium" onDoubleClick={(e) => startFolderRename(e, folder)}>{folder.name}</span>
                    )}
                    <span className="text-xs text-gray-400">{folderNbs.length}</span>
                    {editingFolderId !== folder.id && (
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCreateNotebook(folder.id); }}
                          className="p-0.5 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-gray-400 hover:text-blue-500 transition-all"
                          title={t('notebook.newNotebook')}
                        >
                          <Plus size={12} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteFolder(e, folder.id)}
                          className="p-0.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 transition-all"
                          title={t('common.delete')}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                  {!isCollapsed && (
                    <div className="space-y-0.5">
                      {folderNbs.length === 0 && (
                        <div className="pl-9 py-1 text-xs text-gray-400 italic">{t('sidebar.noData')}</div>
                      )}
                      {folderNbs.map((nb) => renderNotebookItem(nb, true))}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Uncategorized section — drop target for removing from folders */}
            {folders.length > 0 && (
              <div
                onDragOver={handleDragOverUncategorized}
                onDragLeave={handleDragLeave}
                onDrop={handleDropOnUncategorized}
                className={`px-2 pt-2 pb-1 text-xs font-medium uppercase tracking-wider rounded-md transition-colors ${dragOverUncategorized ? 'bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-400 text-blue-600' : 'text-gray-400'}`}
              >
                {t('folder.uncategorized')}
              </div>
            )}
            {uncategorized.map((nb) => renderNotebookItem(nb))}
          </div>
        )}

        {activeTab === 'data' && (
          <div className="space-y-1">
            <button onClick={() => fileInputRef.current?.click()} className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
              <Upload size={14} /> {t('sidebar.uploadCSV')}
            </button>
            <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleUploadCSV} />
            {dataSources.length === 0 ? (
              <div className="px-3 py-4 text-sm text-gray-400 text-center">{t('sidebar.noData')}</div>
            ) : (
              dataSources.map((ds) => (
                <div key={ds.id} className="px-3 py-2 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800">
                  <div className="flex items-center gap-2">
                    <Database size={14} className="text-gray-400" />
                    <span className="truncate">{ds.name}</span>
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">{ds.ds_type}</div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'audit' && canViewAudit && (
          <AuditPanel
            auditEvents={auditEvents}
            auditLoading={auditLoading}
            onRefresh={() => {
              void refreshAudit();
            }}
          />
        )}
      </div>
    </div>
  );
}
