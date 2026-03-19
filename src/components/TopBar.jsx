import { Moon, Sun, Share2, FileDown, BarChart3, PanelLeftOpen } from 'lucide-react';

function formatIdentity(identity) {
  if (!identity || identity === 'local') return 'Local device';
  return identity;
}

export default function TopBar({
  darkMode,
  onToggleTheme,
  onExportPdf,
  onShare,
  onOpenAdmin,
  currentUser,
  onOpenSidebar,
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-700 px-4 py-3 sm:px-5">
      <div className="flex min-w-0 items-start gap-3">
        {onOpenSidebar ? (
          <button
            className="mt-0.5 rounded-md p-2 hover:bg-slate-800 md:hidden"
            onClick={onOpenSidebar}
            title="Open conversations"
            aria-label="Open conversations"
          >
            <PanelLeftOpen size={18} />
          </button>
        ) : null}
        <div className="min-w-0">
        <h1 className="text-base font-semibold sm:text-lg">Agility AI Assistant</h1>
        <p className="mt-1 text-xs text-slate-400">
          Logged in as{' '}
          <span className="font-medium text-emerald-300">{formatIdentity(currentUser?.identity)}</span>
        </p>
        </div>
      </div>
      <div className="flex w-full items-center justify-end gap-2 sm:w-auto">
        <button className="rounded-md p-2 hover:bg-slate-800" onClick={onOpenAdmin} title="Admin dashboard">
          <BarChart3 size={18} />
        </button>
        <button className="rounded-md p-2 hover:bg-slate-800" onClick={onExportPdf} title="Export PDF">
          <FileDown size={18} />
        </button>
        <button className="rounded-md p-2 hover:bg-slate-800" onClick={onShare} title="Share">
          <Share2 size={18} />
        </button>
        <button className="rounded-md p-2 hover:bg-slate-800" onClick={onToggleTheme}>
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </div>
  );
}
