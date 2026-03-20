import { ImagePlus, X } from 'lucide-react';
import { useRef, useState } from 'react';

export default function MessageInput({ onSend, disabled, value, onChange, inputRef, onUploadImage }) {
  const trimmedValue = value.trim();
  const fileInputRef = useRef(null);
  const [pendingImages, setPendingImages] = useState([]);
  const [uploadError, setUploadError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    if (!trimmedValue) return;

    try {
      setUploadError('');
      const uploadedAttachments = [];
      for (const file of pendingImages) {
        const uploaded = onUploadImage ? await onUploadImage(file) : null;
        if (uploaded) uploadedAttachments.push(uploaded);
      }
      await onSend(trimmedValue, uploadedAttachments);
      onChange('');
      setPendingImages([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (error) {
      setUploadError(error?.message || 'Unable to upload image.');
    }
  }

  return (
    <form
      className="sticky bottom-0 z-20 mt-auto border-t border-slate-200/80 bg-white/95 px-3 py-3 backdrop-blur supports-[backdrop-filter]:bg-white/80 dark:border-slate-800 dark:bg-slate-950/95 dark:supports-[backdrop-filter]:bg-slate-950/80 sm:rounded-2xl sm:border sm:px-4 sm:py-4 md:bottom-4 md:px-5 [padding-bottom:calc(0.75rem+env(safe-area-inset-bottom))]"
      onSubmit={handleSubmit}
    >
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex min-w-0 flex-1 gap-2">
          <input
            ref={inputRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Ask Beisser AI..."
            className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-emerald-500 focus:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-emerald-500 dark:focus:bg-slate-950"
          />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            multiple
            className="hidden"
            onChange={(event) => {
              const files = Array.from(event.target.files || []);
              if (!files.length) return;
              setPendingImages((prev) => [...prev, ...files]);
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-3 text-slate-600 transition hover:border-emerald-500 hover:text-emerald-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-emerald-500 dark:hover:text-emerald-300"
            title="Attach image"
          >
            <ImagePlus className="h-5 w-5" />
          </button>
        </div>
        <button
          disabled={disabled || !trimmedValue}
          className="w-full rounded-xl bg-emerald-500 px-4 py-3 font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:min-w-28"
        >
          Send
        </button>
      </div>

      <div className="mx-auto w-full max-w-4xl">
        {pendingImages.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {pendingImages.map((file, index) => (
              <div
                key={`${file.name}-${file.size}-${index}`}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              >
                <span>{file.name}</span>
                <button
                  type="button"
                  onClick={() => setPendingImages((prev) => prev.filter((_, itemIndex) => itemIndex !== index))}
                  className="text-slate-400 transition hover:text-slate-600 dark:hover:text-white"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {uploadError ? <p className="mt-2 text-xs text-rose-300">{uploadError}</p> : null}
        <p className="mt-2 text-[10px] text-slate-400 sm:text-xs">
          Include a text question with your image upload.
        </p>
      </div>
    </form>
  );
}
