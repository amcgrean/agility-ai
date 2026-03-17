import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
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

export default function ChatMessage({ message }) {
  return (
    <article
      className={`max-w-3xl rounded-2xl px-4 py-3 ${message.role === 'user' ? 'ml-auto bg-emerald-600/90 text-white' : 'mr-auto bg-slate-800 text-slate-100'}`}
    >
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
      >
        {message.content || (message.streaming ? '...' : '')}
      </ReactMarkdown>
      <p className="mt-2 text-right text-xs opacity-70">{format(new Date(message.createdAt), 'p')}</p>
    </article>
  );
}
