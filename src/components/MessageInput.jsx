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
      className="flex flex-col gap-2 border-t border-slate-700 p-3 sm:flex-row sm:p-4"
      onSubmit={handleSubmit}
    >
      <div className="flex-1">
        <div className="flex min-w-0 gap-2">
          <input
            ref={inputRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            placeholder="Ask Beisser AI..."
            className="min-w-0 flex-1 rounded-xl border border-slate-600 bg-slate-800 px-4 py-3 outline-none focus:border-emerald-500"
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
            className="rounded-xl border border-slate-600 bg-slate-800 px-3 py-3 text-slate-200 transition hover:border-emerald-400 hover:text-emerald-300"
            title="Attach image"
          >
            <ImagePlus className="h-5 w-5" />
          </button>
        </div>
        {pendingImages.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {pendingImages.map((file, index) => (
              <div
                key={`${file.name}-${file.size}-${index}`}
                className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300"
              >
                <span>{file.name}</span>
                <button
                  type="button"
                  onClick={() => setPendingImages((prev) => prev.filter((_, itemIndex) => itemIndex !== index))}
                  className="text-slate-400 transition hover:text-white"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        ) : null}
        {uploadError ? <p className="mt-2 text-xs text-rose-300">{uploadError}</p> : null}
        <p className="mt-2 text-xs text-slate-400">
          You can attach screenshots now. Image interpretation is the next backend step, so include a text question with the upload.
        </p>
      </div>
      <button
        disabled={disabled || !trimmedValue}
        className="w-full rounded-xl bg-emerald-500 px-4 py-3 font-medium text-white hover:bg-emerald-600 disabled:opacity-60 sm:w-auto sm:py-2"
      >
        Send
      </button>
    </form>
  );
}
