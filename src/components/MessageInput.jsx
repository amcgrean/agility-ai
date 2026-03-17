import { useState } from 'react';

export default function MessageInput({ onSend, disabled }) {
  const [value, setValue] = useState('');

  return (
    <form
      className="flex gap-2 border-t border-slate-700 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!value.trim()) return;
        onSend(value.trim());
        setValue('');
      }}
    >
      <input
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask Agility AI..."
        className="flex-1 rounded-xl border border-slate-600 bg-slate-800 px-4 py-3 outline-none focus:border-emerald-500"
      />
      <button
        disabled={disabled}
        className="rounded-xl bg-emerald-500 px-4 py-2 font-medium text-white hover:bg-emerald-600 disabled:opacity-60"
      >
        Send
      </button>
    </form>
  );
}
