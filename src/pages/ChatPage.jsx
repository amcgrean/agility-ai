import { useEffect, useMemo, useRef, useState } from 'react';
import { jsPDF } from 'jspdf';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/TopBar';
import ChatMessage from '../components/ChatMessage';
import MessageInput from '../components/MessageInput';
import { conversationService } from '../services/api';
import { useChat } from '../hooks/useChat';

export default function ChatPage() {
  const {
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
  } = useChat();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('theme') !== 'light');
  const [currentUser, setCurrentUser] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  useEffect(() => {
    let active = true;

    async function loadCurrentUser() {
      const user = await conversationService.currentUser();
      if (active) setCurrentUser(user);
    }

    loadCurrentUser();
    return () => {
      active = false;
    };
  }, []);

  const messages = useMemo(() => activeConversation?.messages || [], [activeConversation]);

  function exportPdf() {
    if (!activeConversation) return;
    const doc = new jsPDF();
    const content = messages
      .map((message) => `${message.role.toUpperCase()}\n${message.content}\n`)
      .join('\n');
    const lines = doc.splitTextToSize(content || 'No messages', 180);
    doc.text(lines, 10, 10);
    doc.save(`${activeConversation.title || 'conversation'}.pdf`);
  }

  function shareConversation() {
    if (!activeConversationId) return;
    const url = `${window.location.origin}/share/${activeConversationId}`;
    navigator.clipboard.writeText(url);
    alert('Share link copied to clipboard.');
  }

  async function handleSuggestionClick(suggestion, message) {
    setDraft(suggestion);
    inputRef.current?.focus();

    await conversationService.trackEngagement({
      eventType: 'follow_up_selected',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: {
        source: 'assistant_related_questions',
      },
    });
  }

  async function handleMessageDislike(message) {
    await conversationService.trackEngagement({
      eventType: 'response_thumbed_down',
      conversationId: activeConversationId,
      messageId: message.id,
      label: activeConversation?.title || 'assistant_response',
      metadata: {
        source: 'assistant_message',
        responsePreview: (message.content || '').slice(0, 300),
      },
    });
  }

  async function handleMessageLike(message) {
    await conversationService.trackEngagement({
      eventType: 'response_thumbed_up',
      conversationId: activeConversationId,
      messageId: message.id,
      label: activeConversation?.title || 'assistant_response',
      metadata: {
        source: 'assistant_message',
        responsePreview: (message.content || '').slice(0, 300),
      },
    });
  }

  async function handleMessageCorrection(message, correctedAnswer, notes) {
    if (!activeConversationId) {
      throw new Error('Select a conversation before submitting a correction.');
    }

    return conversationService.submitCorrection(activeConversationId, message.id, correctedAnswer, notes);
  }

  async function handleSuggestionLike(suggestion, message) {
    await conversationService.trackEngagement({
      eventType: 'suggestion_thumbed_up',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: {
        source: 'assistant_related_questions',
      },
    });
  }

  async function handleSuggestionDislike(suggestion, message) {
    await conversationService.trackEngagement({
      eventType: 'suggestion_thumbed_down',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: {
        source: 'assistant_related_questions',
      },
    });
  }

  return (
    <main className="flex h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelect={setActiveConversationId}
        onCreate={newConversation}
        onRename={renameConversation}
        onDelete={deleteConversation}
      />

      <section className="flex flex-1 flex-col">
        <TopBar
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode((prev) => !prev)}
          onExportPdf={exportPdf}
          onShare={shareConversation}
          onOpenAdmin={() => navigate('/admin')}
          currentUser={currentUser}
        />

        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <p className="text-sm opacity-70">Start a conversation by asking a question.</p>
          ) : (
            messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onSuggestionClick={handleSuggestionClick}
                onMessageLike={handleMessageLike}
                onMessageDislike={handleMessageDislike}
                onMessageCorrection={handleMessageCorrection}
                onSuggestionLike={handleSuggestionLike}
                onSuggestionDislike={handleSuggestionDislike}
              />
            ))
          )}
        </div>

        <MessageInput
          onSend={sendMessage}
          disabled={isLoading}
          value={draft}
          onChange={setDraft}
          inputRef={inputRef}
        />
      </section>
    </main>
  );
}
