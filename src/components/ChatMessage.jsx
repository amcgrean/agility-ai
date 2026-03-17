import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { Copy, ThumbsDown, ThumbsUp } from 'lucide-react';
import { format } from 'date-fns';

function CodeBlock({ children, className }) {
  const [copied, setCopied] = useState(false);
  const code = String(children).replace(/\n$/, '');

  async function copyCode() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  }

  return (
    <div className="relative my-2 rounded-md bg-black/70">
      <button
        className="absolute right-2 top-2 rounded bg-slate-700 px-2 py-1 text-xs"
        onClick={copyCode}
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className="overflow-x-auto p-3 text-sm">
        <code className={className}>{code}</code>
      </pre>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="space-y-3">
      <div className="inline-flex items-center gap-2 rounded-full bg-slate-700/70 px-3 py-1 text-sm font-medium text-emerald-200">
        <span className="inline-flex gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-300 [animation-delay:-0.2s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-300 [animation-delay:-0.1s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-300" />
        </span>
        Agility AI is drafting a response
      </div>
      <div className="space-y-2">
        <div className="h-3 w-11/12 animate-pulse rounded-full bg-slate-700" />
        <div className="h-3 w-4/5 animate-pulse rounded-full bg-slate-700" />
        <div className="h-3 w-3/5 animate-pulse rounded-full bg-slate-700" />
      </div>
    </div>
  );
}

function extractSuggestions(content = '') {
  const sectionRegex = /(^|\n)##\s+(Related Questions|Want to Learn More\?)\s*\n([\s\S]*?)(?=\n##\s+|\s*$)/i;
  const match = content.match(sectionRegex);
  if (!match) {
    return { body: content, suggestions: [] };
  }

  const body = content.replace(sectionRegex, '').trim();
  const suggestions = match[3]
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim())
    .filter(Boolean);

  return { body, suggestions };
}

export default function ChatMessage({
  message,
  onSuggestionClick,
  onMessageLike,
  onMessageDislike,
  onSuggestionLike,
  onSuggestionDislike,
}) {
  const isUser = message.role === 'user';
  const { body, suggestions } = useMemo(() => extractSuggestions(message.content), [message.content]);
  const showTyping = message.streaming && !body;
  const [messageFeedback, setMessageFeedback] = useState(null);
  const [suggestionFeedback, setSuggestionFeedback] = useState({});
  const [copied, setCopied] = useState(false);

  async function handleCopyResponse() {
    await navigator.clipboard.writeText(message.content || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  }

  async function handleMessageLike() {
    if (messageFeedback) return;
    setMessageFeedback('liked');
    await onMessageLike?.(message);
  }

  async function handleMessageDislike() {
    if (messageFeedback) return;
    setMessageFeedback('disliked');
    await onMessageDislike?.(message);
  }

  async function handleSuggestionLike(suggestion) {
    if (suggestionFeedback[suggestion]) return;
    setSuggestionFeedback((prev) => ({ ...prev, [suggestion]: 'liked' }));
    await onSuggestionLike?.(suggestion, message);
  }

  async function handleSuggestionDislike(suggestion) {
    if (suggestionFeedback[suggestion]) return;
    setSuggestionFeedback((prev) => ({ ...prev, [suggestion]: 'disliked' }));
    await onSuggestionDislike?.(suggestion, message);
  }

  return (
    <article
      className={`max-w-3xl rounded-2xl px-4 py-3 ${
        isUser ? 'ml-auto bg-emerald-600/90 text-white' : 'mr-auto bg-slate-800 text-slate-100'
      }`}
    >
      {!isUser && !showTyping ? (
        <div className="mb-3 flex items-center justify-between gap-3 border-b border-slate-700/70 pb-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Assistant Response
          </p>
          <button
            type="button"
            onClick={handleCopyResponse}
            className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:border-emerald-400 hover:text-emerald-200"
            title="Copy response"
          >
            <Copy className="h-4 w-4" />
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      ) : null}

      {showTyping ? (
        <TypingIndicator />
      ) : (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            code(props) {
              const { children, className, inline } = props;
              return inline ? (
                <code className="rounded bg-slate-700 px-1 py-0.5">{children}</code>
              ) : (
                <CodeBlock className={className}>{children}</CodeBlock>
              );
            },
          }}
          className={
            isUser
              ? 'space-y-3 whitespace-pre-wrap break-words text-[15px] leading-7'
              : 'space-y-4 break-words text-[15px] leading-7 [&_h1]:mb-3 [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:mb-3 [&_h2]:mt-7 [&_h2]:border-b [&_h2]:border-slate-700 [&_h2]:pb-2 [&_h2]:text-xl [&_h2]:font-semibold [&_h3]:mb-2 [&_h3]:mt-5 [&_h3]:text-base [&_h3]:font-semibold [&_p]:my-3 [&_ul]:my-3 [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:space-y-2 [&_ol]:pl-6 [&_li]:my-1 [&_strong]:font-semibold [&_blockquote]:my-4 [&_blockquote]:rounded-r-lg [&_blockquote]:border-l-2 [&_blockquote]:border-slate-500 [&_blockquote]:bg-slate-900/30 [&_blockquote]:pl-4 [&_blockquote]:pr-3 [&_blockquote]:py-2 [&_blockquote]:text-slate-300 [&_table]:my-4 [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-slate-600 [&_th]:bg-slate-700 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_td]:border [&_td]:border-slate-700 [&_td]:px-3 [&_td]:py-2 [&_a]:font-medium [&_a]:text-emerald-300 [&_a]:underline'
          }
        >
          {body || (message.streaming ? 'Generating response...' : '')}
        </ReactMarkdown>
      )}

      {!isUser && suggestions.length > 0 ? (
        <div className="mt-5 border-t border-slate-700 pt-4">
          <p className="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-emerald-300">
            Continue Exploring
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <div key={suggestion} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSuggestionClick?.(suggestion, message)}
                  className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-left text-sm text-emerald-100 transition hover:border-emerald-300 hover:bg-emerald-400/20"
                >
                  {suggestion}
                </button>
                <button
                  type="button"
                  onClick={() => handleSuggestionLike(suggestion)}
                  disabled={Boolean(suggestionFeedback[suggestion])}
                  className="rounded-full border border-slate-600 bg-slate-900/40 p-2 text-slate-300 transition hover:border-emerald-400 hover:text-emerald-300 disabled:cursor-default disabled:border-emerald-500/40 disabled:text-emerald-300"
                  aria-label={`Thumbs up suggestion: ${suggestion}`}
                  title={suggestionFeedback[suggestion] ? 'Feedback recorded' : 'Thumbs up this suggestion'}
                >
                  <ThumbsUp className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => handleSuggestionDislike(suggestion)}
                  disabled={Boolean(suggestionFeedback[suggestion])}
                  className="rounded-full border border-slate-600 bg-slate-900/40 p-2 text-slate-300 transition hover:border-rose-400 hover:text-rose-300 disabled:cursor-default disabled:border-rose-500/40 disabled:text-rose-300"
                  aria-label={`Thumbs down suggestion: ${suggestion}`}
                  title={suggestionFeedback[suggestion] ? 'Feedback recorded' : 'Thumbs down this suggestion'}
                >
                  <ThumbsDown className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {!isUser && !showTyping ? (
        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleMessageLike}
              disabled={Boolean(messageFeedback)}
              className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:border-emerald-400 hover:text-emerald-300 disabled:cursor-default disabled:border-emerald-500/40 disabled:text-emerald-300"
              title={messageFeedback ? 'Feedback recorded' : 'Thumbs up this answer'}
            >
              <ThumbsUp className="h-4 w-4" />
              {messageFeedback === 'liked' ? 'Liked' : 'Thumbs up'}
            </button>
            <button
              type="button"
              onClick={handleMessageDislike}
              disabled={Boolean(messageFeedback)}
              className="inline-flex items-center gap-2 rounded-full border border-slate-600 px-3 py-1.5 text-xs text-slate-300 transition hover:border-rose-400 hover:text-rose-300 disabled:cursor-default disabled:border-rose-500/40 disabled:text-rose-300"
              title={messageFeedback ? 'Feedback recorded' : 'Thumbs down this answer'}
            >
              <ThumbsDown className="h-4 w-4" />
              {messageFeedback === 'disliked' ? 'Disliked' : 'Thumbs down'}
            </button>
          </div>
          <p className="text-right text-xs opacity-70">{format(new Date(message.createdAt), 'p')}</p>
        </div>
      ) : (
        <p className="mt-2 text-right text-xs opacity-70">{format(new Date(message.createdAt), 'p')}</p>
      )}
    </article>
  );
}
