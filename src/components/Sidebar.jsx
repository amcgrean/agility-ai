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
}) {
  const [editing, setEditing] = useState(null);
  const [title, setTitle] = useState('');

  return (
    <aside
      className={`border-r border-slate-700 bg-slate-900/80 p-3 transition-all duration-200 dark:text-slate-100 ${collapsed ? 'w-16' : 'w-72'}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <button
          onClick={onToggle}
          className="rounded-md p-2 hover:bg-slate-800"
          aria-label="Toggle sidebar"
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
        {!collapsed && (
          <button
            className="flex items-center gap-2 rounded-md bg-emerald-500 px-3 py-2 text-sm text-white hover:bg-emerald-600"
            onClick={onCreate}
          >
            <Plus size={16} /> New chat
          </button>
        )}
      </div>

      {!collapsed && (
        <ul className="space-y-2">
          {conversations.map((conversation) => (
            <li
              key={conversation.id}
              className={`group rounded-md p-2 ${conversation.id === activeConversationId ? 'bg-slate-700' : 'hover:bg-slate-800'}`}
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
                    className="truncate text-left text-sm"
                    onClick={() => onSelect(conversation.id)}
                  >
                    {conversation.title}
                  </button>
                  <div className="hidden items-center gap-1 group-hover:flex">
                    <button
                      onClick={() => {
                        setEditing(conversation.id);
                        setTitle(conversation.title);
                      }}
                    >
                      <Pencil size={14} />
                    </button>
                    <button onClick={() => onDelete(conversation.id)}>
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
  );
}
