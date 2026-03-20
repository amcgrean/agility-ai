import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
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

  useEffect(() => {
    function handleResize() {
      if (window.innerWidth >= 768) {
        setMobileSidebarOpen(false);
      }
    }

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const messages = useMemo(() => activeConversation?.messages || [], [activeConversation]);

  const exportPdf = useCallback(() => {
    if (!activeConversation) return;
    const doc = new jsPDF();
    const content = messages
      .map((message) => `${message.role.toUpperCase()}\n${message.content}\n`)
      .join('\n');
    const lines = doc.splitTextToSize(content || 'No messages', 180);
    doc.text(lines, 10, 10);
    doc.save(`${activeConversation.title || 'conversation'}.pdf`);
  }, [activeConversation, messages]);

  const shareConversation = useCallback(() => {
    if (!activeConversationId) return;
    const url = `${window.location.origin}/share/${activeConversationId}`;
    navigator.clipboard.writeText(url);
    alert('Share link copied to clipboard.');
  }, [activeConversationId]);

  const handleSuggestionClick = useCallback(async (suggestion, message) => {
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
  }, [activeConversationId, setDraft]);

  const handleMessageDislike = useCallback(async (message) => {
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
  }, [activeConversationId, activeConversation?.title]);

  const handleMessageLike = useCallback(async (message) => {
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
  }, [activeConversationId, activeConversation?.title]);

  const handleMessageCorrection = useCallback(async (message, correctedAnswer, notes) => {
    if (!activeConversationId) {
      throw new Error('Select a conversation before submitting a correction.');
    }

    return conversationService.submitCorrection(activeConversationId, message.id, correctedAnswer, notes);
  }, [activeConversationId]);

  const handleSuggestionLike = useCallback(async (suggestion, message) => {
    await conversationService.trackEngagement({
      eventType: 'suggestion_thumbed_up',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: {
        source: 'assistant_related_questions',
      },
    });
  }, [activeConversationId]);

  const handleSuggestionDislike = useCallback(async (suggestion, message) => {
    await conversationService.trackEngagement({
      eventType: 'suggestion_thumbed_down',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: {
        source: 'assistant_related_questions',
      },
    });
  }, [activeConversationId]);

  return (
    <main className="flex min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelect={setActiveConversationId}
        onCreate={newConversation}
        onRename={renameConversation}
        onDelete={deleteConversation}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <section className="flex min-h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode((prev) => !prev)}
          onExportPdf={exportPdf}
          onShare={shareConversation}
          onOpenAdmin={() => navigate('/admin')}
          currentUser={currentUser}
          onOpenSidebar={() => setMobileSidebarOpen(true)}
        />

        <div className="mx-auto flex w-full max-w-5xl flex-1 min-w-0 flex-col px-3 pb-3 sm:px-4 sm:pb-4 md:px-6 md:pb-6">
          <div className="flex-1 overflow-y-auto pt-3 sm:pt-4 md:pt-6">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 pb-4 md:pb-6">
              {messages.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white/70 px-4 py-6 text-sm text-slate-600 shadow-sm dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300 sm:px-6">
                  Start a conversation by asking a question.
                </div>
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
          </div>

          <MessageInput
            onSend={sendMessage}
            disabled={isLoading}
            value={draft}
            onChange={setDraft}
            inputRef={inputRef}
          />
        </div>
      </section>
    </main>
  );
}
