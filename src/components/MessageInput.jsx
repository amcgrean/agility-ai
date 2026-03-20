export default function MessageInput({ onSend, disabled, value, onChange, inputRef }) {
  const trimmedValue = value.trim();

  return (
    <form
      className="sticky bottom-0 z-20 mt-auto border-t border-slate-200/80 bg-white/95 px-3 py-3 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:border-slate-800 dark:bg-slate-950/95 dark:supports-[backdrop-filter]:bg-slate-950/80 sm:rounded-2xl sm:border sm:px-4 sm:py-4 md:bottom-4 md:px-5 [padding-bottom:calc(0.75rem+env(safe-area-inset-bottom))]"
      onSubmit={(event) => {
        event.preventDefault();
        if (!trimmedValue) return;
        onSend(trimmedValue);
        onChange('');
      }}
    >
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-2 sm:flex-row sm:items-end">
        <input
          ref={inputRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask Agility AI..."
          className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-500 focus:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-emerald-500 dark:focus:bg-slate-950"
        />
        <button
          disabled={disabled || !trimmedValue}
          className="w-full rounded-xl bg-emerald-500 px-4 py-3 font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:min-w-28"
        >
          Send
        </button>
      </div>
    </form>
  );
}
