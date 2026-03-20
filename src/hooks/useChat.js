import { useEffect, useMemo, useState } from 'react';
import { conversationService } from '../services/api';

export function useChat() {
  const [conversations, setConversations] = useState([]);
  const [folders, setFolders] = useState([]);
  const [promptStarters, setPromptStarters] = useState({
    starters: [],
    trendingQuestions: [],
    relatedTopics: [],
  });
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [draft, setDraft] = useState('');

  useEffect(() => {
    async function init() {
      const [folderList, conversationList, starterData] = await Promise.all([
        conversationService.listFolders(),
        conversationService.list(),
        conversationService.getPromptStarters(),
      ]);
      setFolders(folderList);
      setConversations(conversationList);
      setPromptStarters(starterData);
      if (conversationList.length > 0) setActiveConversationId(conversationList[0].id);
    }

    init();
  }, []);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) || null,
    [conversations, activeConversationId],
  );

  function updateConversation(conversationId, updater) {
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId ? updater(conversation) : conversation,
      ),
    );
  }

  async function refreshPromptStarters() {
    const next = await conversationService.getPromptStarters();
    setPromptStarters(next);
    return next;
  }

  async function newConversation(folderId = null) {
    const created = await conversationService.create(folderId ? { folderId } : {});
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

  async function moveConversation(conversationId, folderId) {
    const updatedConversation = await conversationService.update(conversationId, {
      folderId: folderId || null,
    });
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, folderId: updatedConversation?.folderId ?? null } : conversation,
      ),
    );
  }

  async function createFolder(title) {
    const created = await conversationService.createFolder(title);
    setFolders((prev) => [created, ...prev]);
    return created;
  }

  async function renameFolder(folderId, title) {
    const updated = await conversationService.updateFolder(folderId, { title });
    setFolders((prev) => prev.map((folder) => (folder.id === folderId ? updated : folder)));
  }

  async function deleteFolder(folderId) {
    await conversationService.deleteFolder(folderId);
    setFolders((prev) => prev.filter((folder) => folder.id !== folderId));
    setConversations((prev) =>
      prev.map((conversation) => (conversation.folderId === folderId ? { ...conversation, folderId: null } : conversation)),
    );
  }

  async function sendMessage(question, attachments = []) {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;

    let conversationId = activeConversationId || conversations[0]?.id;
    if (!conversationId) {
      const created = await newConversation();
      conversationId = created?.id || null;
    }

    if (!conversationId) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmedQuestion,
      createdAt: new Date().toISOString(),
      attachments,
    };

    updateConversation(conversationId, (conversation) => ({
      ...conversation,
      messages: [...(conversation.messages || []), userMessage],
    }));
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

    updateConversation(conversationId, (conversation) => ({
      ...conversation,
      messages: [...(conversation.messages || []), assistantShell],
    }));

    setIsLoading(true);
    try {
      const response = await conversationService.ask(trimmedQuestion, conversationId);
      const answer = response.answer || '';
      const finalMessage = {
        ...assistantShell,
        content: answer,
        streaming: false,
        suggestions: response.followUpQuestions || [],
      };
      updateConversation(conversationId, (conversation) => ({
        ...conversation,
        messages: (conversation.messages || []).map((msg) =>
          msg.id === assistantMessageId ? finalMessage : msg,
        ),
      }));
      const assistantAppendResult = await conversationService.appendMessage(conversationId, finalMessage);
      applyConversationTitle(conversationId, assistantAppendResult?.conversationTitle);
      if (response.promptStarters) {
        setPromptStarters(response.promptStarters);
      }
    } catch (error) {
      const errorMessage = error?.message || 'Something went wrong while processing that question.';
      updateConversation(conversationId, (conversation) => ({
        ...conversation,
        messages: (conversation.messages || []).map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: `## Short Answer\n\n${errorMessage}\n\n## Key Details\n\nPlease try again in a moment.`,
                streaming: false,
                error: true,
              }
            : msg,
        ),
      }));
      throw error;
    } finally {
      setIsLoading(false);
    }

    await refreshPromptStarters();
  }

  return {
    conversations,
    folders,
    promptStarters,
    activeConversation,
    activeConversationId,
    setActiveConversationId,
    draft,
    setDraft,
    newConversation,
    moveConversation,
    renameConversation,
    deleteConversation,
    createFolder,
    renameFolder,
    deleteFolder,
    sendMessage,
    isLoading,
    refreshPromptStarters,
  };
}
