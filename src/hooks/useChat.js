import { useEffect, useMemo, useState } from 'react';
import { conversationService } from '../services/api';

export function useChat() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function init() {
      const list = await conversationService.list();
      setConversations(list);
      if (list.length > 0) setActiveConversationId(list[0].id);
    }

    init();
  }, []);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) || null,
    [conversations, activeConversationId],
  );

  async function newConversation() {
    const created = await conversationService.create();
    setConversations((prev) => [created, ...prev]);
    setActiveConversationId(created.id);
  }

  async function renameConversation(conversationId, title) {
    await conversationService.update(conversationId, { title });
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, title } : conversation,
      ),
    );
  }

  async function deleteConversation(conversationId) {
    await conversationService.remove(conversationId);
    setConversations((prev) => prev.filter((conversation) => conversation.id !== conversationId));
    setActiveConversationId((prev) => (prev === conversationId ? conversations[0]?.id || null : prev));
  }

  async function sendMessage(question) {
    if (!activeConversationId) await newConversation();
    const conversationId = activeConversationId || conversations[0]?.id;
    if (!conversationId) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    };

    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, messages: [...(conversation.messages || []), userMessage] }
          : conversation,
      ),
    );
    await conversationService.appendMessage(conversationId, userMessage);

    const assistantMessageId = crypto.randomUUID();
    const assistantShell = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      streaming: true,
    };

    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, messages: [...(conversation.messages || []), assistantShell] }
          : conversation,
      ),
    );

    setIsLoading(true);
    try {
      const answer = await conversationService.ask(question);
      for (let i = 0; i <= answer.length; i += 4) {
        const partial = answer.slice(0, i);
        setConversations((prev) =>
          prev.map((conversation) => {
            if (conversation.id !== conversationId) return conversation;
            return {
              ...conversation,
              messages: (conversation.messages || []).map((msg) =>
                msg.id === assistantMessageId ? { ...msg, content: partial, streaming: i < answer.length } : msg,
              ),
            };
          }),
        );
        await new Promise((resolve) => setTimeout(resolve, 16));
      }

      const finalMessage = {
        ...assistantShell,
        content: answer,
        streaming: false,
      };
      await conversationService.appendMessage(conversationId, finalMessage);
    } finally {
      setIsLoading(false);
    }
  }

  return {
    conversations,
    activeConversation,
    activeConversationId,
    setActiveConversationId,
    newConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    isLoading,
  };
}
