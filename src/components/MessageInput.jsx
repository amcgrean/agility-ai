export default function MessageInput({ onSend, disabled, value, onChange, inputRef }) {
  const trimmedValue = value.trim();

  return (
    <form
      className="flex gap-2 border-t border-slate-700 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!trimmedValue) return;
        onSend(trimmedValue);
        onChange('');
      }}
    >
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask Agility AI..."
        className="flex-1 rounded-xl border border-slate-600 bg-slate-800 px-4 py-3 outline-none focus:border-emerald-500"
      />
      <button
        disabled={disabled || !trimmedValue}
        className="rounded-xl bg-emerald-500 px-4 py-2 font-medium text-white hover:bg-emerald-600 disabled:opacity-60"
      >
        Send
      </button>
    </form>
  );
}
