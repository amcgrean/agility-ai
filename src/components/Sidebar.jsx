import { FolderPlus, PanelLeftClose, PanelLeftOpen, Pencil, Plus, Trash2, BarChart3, MessageSquare } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

function ConversationRow({
  conversation,
  activeConversationId,
  folders,
  editing,
  title,
  setTitle,
  setEditing,
  onSelect,
  onRename,
  onDelete,
  onMove,
  onCloseMobile,
}) {
  const isActive = conversation.id === activeConversationId;

  return (
    <li className={`group rounded-md p-2 ${isActive ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>
      {editing === conversation.id ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onRename(conversation.id, title || 'Untitled');
            setEditing(null);
          }}
        >
          <input
            autoFocus
            className="w-full rounded bg-slate-600 px-2 py-1 text-sm"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            onBlur={() => setEditing(null)}
          />
        </form>
      ) : (
        <>
          <div className="flex items-center justify-between gap-2">
            <button
              className="min-w-0 flex-1 truncate text-left text-sm"
              onClick={() => {
                onSelect(conversation.id);
                onCloseMobile?.();
              }}
            >
              {conversation.title}
            </button>
            <div className="flex items-center gap-1 opacity-100 md:opacity-0 md:transition md:group-hover:opacity-100">
              <button
                onClick={() => {
                  setEditing(conversation.id);
                  setTitle(conversation.title);
                }}
                className="rounded p-1 hover:bg-slate-700"
              >
                <Pencil size={14} />
              </button>
              <button onClick={() => onDelete(conversation.id)} className="rounded p-1 hover:bg-slate-700">
                <Trash2 size={14} />
              </button>
            </div>
          </div>
          {isActive ? (
            <select
              className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
              value={conversation.folderId || ''}
              onChange={(event) => onMove(conversation.id, event.target.value || null)}
            >
              <option value="">No folder</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.title}
                </option>
              ))}
            </select>
          ) : null}
        </>
      )}
    </li>
  );
}

function FolderSection({
  label,
  items,
  folderMeta,
  folders,
  activeConversationId,
  editing,
  title,
  setTitle,
  setEditing,
  onSelect,
  onRenameConversation,
  onDeleteConversation,
  onMoveConversation,
  onCloseMobile,
  onRenameFolder,
  onDeleteFolder,
}) {
  if (!items.length) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-2">
        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">{label}</p>
        {folderMeta ? (
          <div className="flex items-center gap-1">
            <button
              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              onClick={() => {
                const nextTitle = window.prompt('Rename folder', folderMeta.title);
                if (nextTitle?.trim()) onRenameFolder(folderMeta.id, nextTitle.trim());
              }}
            >
              <Pencil size={13} />
            </button>
            <button
              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              onClick={() => {
                if (window.confirm(`Delete folder "${folderMeta.title}"? Chats will be moved to No folder.`)) {
                  onDeleteFolder(folderMeta.id);
                }
              }}
            >
              <Trash2 size={13} />
            </button>
          </div>
        ) : null}
      </div>
      <ul className="space-y-2">
        {items.map((conversation) => (
          <ConversationRow
            key={conversation.id}
            conversation={conversation}
            activeConversationId={activeConversationId}
            folders={folders}
            editing={editing}
            title={title}
            setTitle={setTitle}
            setEditing={setEditing}
            onSelect={onSelect}
            onRename={onRenameConversation}
            onDelete={onDeleteConversation}
            onMove={onMoveConversation}
            onCloseMobile={onCloseMobile}
          />
        ))}
      </ul>
    </div>
  );
}

export default function Sidebar({
  conversations,
  folders,
  activeConversationId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onMoveConversation,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  collapsed,
  onToggle,
  mobileOpen,
  onCloseMobile,
}) {
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState('');
  const location = useLocation();

  const isReporting = location.pathname === '/reporting';
  const isGeneral = location.pathname === '/';

  const grouped = useMemo(() => {
    const byFolder = folders
      .map((folder) => ({
        folder,
        items: conversations.filter((conversation) => conversation.folderId === folder.id),
      }))
      .filter((group) => group.items.length > 0);

    const unfiled = conversations.filter((conversation) => !conversation.folderId);
    return { byFolder, unfiled };
  }, [conversations, folders]);

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-slate-950/60 backdrop-blur-sm md:hidden"
          onClick={onCloseMobile}
          aria-label="Close conversation list"
        />
      ) : null}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh flex-col border-r border-slate-700 bg-slate-900/95 p-3 text-slate-100 shadow-2xl shadow-slate-950/40 transition-transform duration-200 md:static md:z-auto md:h-dvh md:translate-x-0 md:bg-slate-900/85 md:shadow-none ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${collapsed ? 'md:w-16' : 'md:w-80'} w-[min(21rem,calc(100vw-2rem))]`}
      >
        <div className="mb-6 flex items-center justify-between gap-2">
          <button
            onClick={onToggle}
            className="hidden rounded-md p-2 hover:bg-slate-800 md:inline-flex"
            aria-label="Toggle sidebar"
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
          <div className="flex flex-1 items-center justify-between gap-2 md:justify-end">
            <p className={`text-sm font-semibold text-slate-300 md:hidden ${collapsed ? 'sr-only' : ''}`}>
              Agility AI
            </p>
            {!collapsed && (
              <button
                className="flex items-center gap-2 rounded-md bg-emerald-500 px-3 py-2 text-sm text-white transition hover:bg-emerald-600"
                onClick={() => {
                  onCreate();
                  onCloseMobile?.();
                }}
              >
                <Plus size={16} /> New chat
              </button>
            )}
          </div>
        </div>

        {!collapsed && (
          <nav className="mb-6 space-y-1">
            <Link
              to="/"
              onClick={onCloseMobile}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isGeneral ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <MessageSquare size={18} className={isGeneral ? 'text-emerald-400' : ''} />
              General Chat
            </Link>
            <Link
              to="/reporting"
              onClick={onCloseMobile}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isReporting ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <BarChart3 size={18} className={isReporting ? 'text-blue-400' : ''} />
              Reporting Expert
            </Link>
          </nav>
        )}

        {!collapsed && (
          <div className="mb-3 flex items-center justify-between px-2">
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">History</p>
            <button
              className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              onClick={async () => {
                const nextTitle = window.prompt('Folder name');
                if (nextTitle?.trim()) await onCreateFolder(nextTitle.trim());
              }}
              title="Create Folder"
            >
              <FolderPlus size={15} />
            </button>
          </div>
        )}

        {!collapsed && (
          <div className="space-y-4 overflow-y-auto pr-1">
            {grouped.byFolder.map((group) => (
              <FolderSection
                key={group.folder.id}
                label={group.folder.title}
                items={group.items}
                folderMeta={group.folder}
                folders={folders}
                activeConversationId={activeConversationId}
                editing={editing}
                title={title}
                setTitle={setTitle}
                setEditing={setEditing}
                onSelect={onSelect}
                onRenameConversation={onRename}
                onDeleteConversation={onDelete}
                onMoveConversation={onMoveConversation}
                onCloseMobile={onCloseMobile}
                onRenameFolder={onRenameFolder}
                onDeleteFolder={onDeleteFolder}
              />
            ))}
            <FolderSection
              label="No folder"
              items={grouped.unfiled}
              folderMeta={null}
              folders={folders}
              activeConversationId={activeConversationId}
              editing={editing}
              title={title}
              setTitle={setTitle}
              setEditing={setEditing}
              onSelect={onSelect}
              onRenameConversation={onRename}
              onDeleteConversation={onDelete}
              onMoveConversation={onMoveConversation}
              onCloseMobile={onCloseMobile}
              onRenameFolder={onRenameFolder}
              onDeleteFolder={onDeleteFolder}
            />
          </div>
        )}
      </aside>
    </>
  );
}
