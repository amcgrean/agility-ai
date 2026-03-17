import { Moon, Sun, Share2, FileDown } from 'lucide-react';

function formatIdentity(identity) {
  if (!identity || identity === 'local') return 'Local device';
  return identity;
}

export default function TopBar({ darkMode, onToggleTheme, onExportPdf, onShare, currentUser }) {
  return (
    <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
      <div>
        <h1 className="text-lg font-semibold">Agility AI Assistant</h1>
        <p className="mt-1 text-xs text-slate-400">
          Logged in as <span className="font-medium text-emerald-300">{formatIdentity(currentUser?.identity)}</span>
        </p>
      </div>
      <div className="flex items-center gap-2">
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
