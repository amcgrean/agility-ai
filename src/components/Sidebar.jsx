import { Plus, Pencil, Trash2, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useState } from 'react';

export default function Sidebar({
  conversations,
  activeConversationId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  collapsed,
  onToggle,
  mobileOpen,
  onCloseMobile,
}) {
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState('');

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
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh flex-col border-r border-slate-700 bg-slate-900/95 p-3 text-slate-100 shadow-2xl shadow-slate-950/40 transition-transform duration-200 md:static md:z-auto md:h-auto md:min-h-screen md:translate-x-0 md:bg-slate-900/85 md:shadow-none ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        } ${collapsed ? 'md:w-16' : 'md:w-72'} w-[min(20rem,calc(100vw-2rem))]`}
      >
        <div className="mb-3 flex items-center justify-between gap-2">
          <button
            onClick={onToggle}
            className="hidden rounded-md p-2 hover:bg-slate-800 md:inline-flex"
            aria-label="Toggle sidebar"
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
          <div className="flex flex-1 items-center justify-between gap-2 md:justify-end">
            <p className={`text-sm font-semibold text-slate-300 md:hidden ${collapsed ? 'sr-only' : ''}`}>
              Conversations
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
          <ul className="space-y-2 overflow-y-auto pr-1">
            {conversations.map((conversation) => (
              <li
                key={conversation.id}
                className={`group rounded-md p-2 transition ${conversation.id === activeConversationId ? 'bg-slate-700' : 'hover:bg-slate-800'}`}
              >
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
                      <button
                        onClick={() => onDelete(conversation.id)}
                        className="rounded p-1 hover:bg-slate-700"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </aside>
    </>
  );
}
