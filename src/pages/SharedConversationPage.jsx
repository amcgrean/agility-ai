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
    <main className="mx-auto min-h-screen max-w-4xl p-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Shared conversation</h1>
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
    </main>
  );
}
