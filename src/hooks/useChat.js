import { useEffect, useMemo, useState } from 'react';
import { conversationService } from '../services/api';

export function useChat() {
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [draft, setDraft] = useState('');

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
    return created;
  }

  function applyConversationTitle(conversationId, title) {
    if (!title) return;
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, title } : conversation,
      ),
    );
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
    setConversations((prev) => {
      const nextConversations = prev.filter((conversation) => conversation.id !== conversationId);
      setActiveConversationId((prevActiveId) => {
        if (prevActiveId !== conversationId) return prevActiveId;
        return nextConversations[0]?.id || null;
      });
      return nextConversations;
    });
  }

  async function sendMessage(question) {
    let conversationId = activeConversationId || conversations[0]?.id;
    if (!conversationId) {
      const created = await newConversation();
      conversationId = created?.id || null;
    }

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
    const userAppendResult = await conversationService.appendMessage(conversationId, userMessage);
    applyConversationTitle(conversationId, userAppendResult?.conversationTitle);

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
      const answer = await conversationService.ask(question, conversationId);
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
      const assistantAppendResult = await conversationService.appendMessage(conversationId, finalMessage);
      applyConversationTitle(conversationId, assistantAppendResult?.conversationTitle);
    } finally {
      setIsLoading(false);
    }
  }

  return {
    conversations,
    activeConversation,
    activeConversationId,
    setActiveConversationId,
    draft,
    setDraft,
    newConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    isLoading,
  };
}
