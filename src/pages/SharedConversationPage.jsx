import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ChatMessage from '../components/ChatMessage';
import { conversationService } from '../services/api';

export default function SharedConversationPage() {
  const { conversationId } = useParams();
  const [conversation, setConversation] = useState(null);

  useEffect(() => {
    async function load() {
      const conversations = await conversationService.list();
      setConversation(conversations.find((item) => item.id === conversationId) || null);
    }
    load();
  }, [conversationId]);

  return (
    <main className="min-h-screen bg-slate-50 px-3 py-4 text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-6 sm:py-6">
      <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-semibold sm:text-2xl">Shared conversation</h1>
        <Link className="text-emerald-500 hover:underline" to="/">
          Open assistant
        </Link>
      </div>

      {conversation ? (
        <div className="space-y-4">
          {conversation.messages?.map((message) => <ChatMessage key={message.id} message={message} />)}
        </div>
      ) : (
        <p>Conversation not found.</p>
      )}
      </div>
    </main>
  );
}
