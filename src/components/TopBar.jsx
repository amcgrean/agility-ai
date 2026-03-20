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
    <div className="border-b border-slate-200/80 bg-white/90 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:border-slate-800 dark:bg-slate-950/90 dark:supports-[backdrop-filter]:bg-slate-950/80 sm:px-5">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          {onOpenSidebar ? (
            <button
              className="mt-0.5 rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800 md:hidden"
              onClick={onOpenSidebar}
              title="Open conversations"
              aria-label="Open conversations"
            >
              <PanelLeftOpen size={18} />
            </button>
          ) : null}
          <div className="min-w-0">
            <h1 className="text-base font-semibold sm:text-lg">Beisser AI Assistant</h1>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Logged in as{' '}
              <span className="font-medium text-emerald-600 dark:text-emerald-300">{formatIdentity(currentUser?.identity)}</span>
            </p>
          </div>
        </div>
        <div className="flex w-full flex-wrap items-center justify-end gap-2 sm:w-auto sm:flex-nowrap">
          <button className="rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={onOpenAdmin} title="Admin dashboard">
            <BarChart3 size={18} />
          </button>
          <button className="rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={onExportPdf} title="Export PDF">
            <FileDown size={18} />
          </button>
          <button className="rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={onShare} title="Share">
            <Share2 size={18} />
          </button>
          <button className="rounded-md p-2 hover:bg-slate-100 dark:hover:bg-slate-800" onClick={onToggleTheme}>
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
