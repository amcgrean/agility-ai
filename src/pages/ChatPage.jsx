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
  const starterCards = promptStarters?.starters || [];
  const trendingQuestions = promptStarters?.trendingQuestions || [];
  const relatedTopics = promptStarters?.relatedTopics || [];

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

  async function handlePromptStarterClick(label, source) {
    setDraft(label);
    inputRef.current?.focus();

    await conversationService.trackEngagement({
      eventType: 'prompt_starter_selected',
      conversationId: activeConversationId,
      label,
      metadata: {
        source,
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
    <main className="flex min-h-screen bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
        conversations={conversations}
        folders={folders}
        activeConversationId={activeConversationId}
        onSelect={setActiveConversationId}
        onCreate={newConversation}
        onRename={renameConversation}
        onDelete={deleteConversation}
        onMoveConversation={moveConversation}
        onCreateFolder={createFolder}
        onRenameFolder={renameFolder}
        onDeleteFolder={deleteFolder}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      <section className="flex min-h-screen min-w-0 flex-1 flex-col">
        <TopBar
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode((prev) => !prev)}
          onExportPdf={exportPdf}
          onShare={shareConversation}
          onOpenAdmin={() => navigate('/admin')}
          currentUser={currentUser}
          onOpenSidebar={() => setMobileSidebarOpen(true)}
        />

        <div className="flex-1 space-y-4 overflow-y-auto p-3 sm:p-4 md:p-6">
          {messages.length === 0 ? (
            <section className="mx-auto max-w-4xl space-y-6">
              <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
                <p className="text-xs uppercase tracking-[0.24em] text-emerald-300">Chat workflow ready</p>
                <h2 className="mt-3 text-2xl font-semibold text-white">Start with a prompt, trend, or related topic</h2>
                <p className="mt-2 max-w-2xl text-sm text-slate-400">
                  Beisser AI now tracks question trends, follow-up selections, thumbs feedback, and explicit answer corrections.
                </p>
                {starterCards.length > 0 ? (
                  <div className="mt-5 flex flex-wrap gap-3">
                    {starterCards.map((item) => (
                      <button
                        key={`${item.source}-${item.label}`}
                        type="button"
                        onClick={() => handlePromptStarterClick(item.label, item.source)}
                        className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-100 transition hover:border-emerald-400 hover:bg-emerald-500/20"
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Trending Questions</p>
                  <div className="mt-4 space-y-3">
                    {trendingQuestions.length > 0 ? (
                      trendingQuestions.map((item) => (
                        <button
                          key={`${item.label}-${item.lastAskedAt}`}
                          type="button"
                          onClick={() => handlePromptStarterClick(item.label, 'trending_question')}
                          className="block w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-left transition hover:border-emerald-500/40"
                        >
                          <p className="text-sm font-medium text-white">{item.label}</p>
                          <p className="mt-1 text-xs text-slate-400">{item.count} asks in the last 30 days</p>
                        </button>
                      ))
                    ) : (
                      <p className="text-sm text-slate-400">Trending questions will appear once people start asking repeat questions.</p>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Related Topics</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    {relatedTopics.length > 0 ? (
                      relatedTopics.map((item) => (
                        <button
                          key={`${item.label}-${item.lastUsedAt}`}
                          type="button"
                          onClick={() => handlePromptStarterClick(item.label, item.source)}
                          className="rounded-full border border-slate-700 bg-slate-950/70 px-4 py-2 text-sm text-slate-200 transition hover:border-emerald-500/40 hover:text-emerald-200"
                        >
                          {item.label}
                        </button>
                      ))
                    ) : (
                      <p className="text-sm text-slate-400">Related topics will populate from the follow-up questions people actually choose.</p>
                    )}
                  </div>
                </div>
              </div>
            </section>
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
          onUploadImage={(file) => conversationService.uploadImage(file, activeConversationId)}
        />
      </section>
    </main>
  );
}
