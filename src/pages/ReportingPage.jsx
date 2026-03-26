import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { jsPDF } from 'jspdf';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import TopBar from '../components/TopBar';
import ChatMessage from '../components/ChatMessage';
import MessageInput from '../components/MessageInput';
import { conversationService } from '../services/api';
import { useChat } from '../hooks/useChat';

export default function ReportingPage() {
  const {
    conversations,
    folders,
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
  const bottomRef = useRef(null);
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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const exportPdf = useCallback(() => {
    if (!activeConversation) return;
    const doc = new jsPDF();
    const content = messages
      .map((message) => `${message.role.toUpperCase()}\n${message.content}\n`)
      .join('\n');
    const lines = doc.splitTextToSize(content || 'No messages', 180);
    doc.text(lines, 10, 10);
    doc.save(`${activeConversation.title || 'reporting-session'}.pdf`);
  }, [activeConversation, messages]);

  const shareConversation = useCallback(() => {
    if (!activeConversationId) return;
    const url = `${window.location.origin}/share/${activeConversationId}`;
    navigator.clipboard.writeText(url);
    alert('Share link copied to clipboard.');
  }, [activeConversationId]);

  const handleSendMessage = useCallback((text, attachments) => {
    sendMessage(text, attachments, 'reporting');
  }, [sendMessage]);

  const handleSuggestionClick = useCallback(async (suggestion, message) => {
    conversationService.trackEngagement({
      eventType: 'follow_up_selected',
      conversationId: activeConversationId,
      messageId: message.id,
      label: suggestion,
      metadata: { source: 'reporting_related_questions', mode: 'reporting' },
    });
    sendMessage(suggestion, [], 'reporting');
  }, [activeConversationId, sendMessage]);

  const handleMessageDislike = useCallback(async (message) => {
    await conversationService.trackEngagement({
      eventType: 'response_thumbed_down',
      conversationId: activeConversationId,
      messageId: message.id,
      label: activeConversation?.title || 'reporting_response',
      metadata: {
        source: 'reporting_expert',
        mode: 'reporting',
        responsePreview: (message.content || '').slice(0, 300),
      },
    });
  }, [activeConversationId, activeConversation?.title]);

  const handleMessageLike = useCallback(async (message) => {
    await conversationService.trackEngagement({
      eventType: 'response_thumbed_up',
      conversationId: activeConversationId,
      messageId: message.id,
      label: activeConversation?.title || 'reporting_response',
      metadata: {
        source: 'reporting_expert',
        mode: 'reporting',
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

  const reportingPrompts = [
    { label: "How do I join item activity to orders?", icon: "📊" },
    { label: "What is the grain of the so_detail table?", icon: "🎯" },
    { label: "Give me a template for a sales by customer report", icon: "📑" },
    { label: "Show business key joins for shipments", icon: "🔗" }
  ];

  return (
    <main className="flex h-dvh overflow-hidden bg-slate-100 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
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

      <section className="flex h-dvh min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar
          darkMode={darkMode}
          onToggleTheme={() => setDarkMode((prev) => !prev)}
          onExportPdf={exportPdf}
          onShare={shareConversation}
          onOpenAdmin={() => navigate('/admin')}
          currentUser={currentUser}
          onOpenSidebar={() => setMobileSidebarOpen(true)}
        />

        <div className="mx-auto flex w-full max-w-5xl flex-1 min-h-0 flex-col px-3 pb-3 sm:px-4 sm:pb-4 md:px-6 md:pb-6">
          <div className="flex-1 min-h-0 overflow-y-auto pt-3 sm:pt-4 md:pt-6">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 pb-4 md:pb-6">
              {messages.length === 0 ? (
                <section className="space-y-6">
                  <div className="rounded-3xl border border-blue-500/20 bg-blue-500/5 p-6 shadow-sm dark:border-blue-500/30 dark:bg-blue-900/10 sm:p-8">
                    <p className="text-xs font-bold uppercase tracking-[0.24em] text-blue-600 dark:text-blue-400">Reporting Expert Mode</p>
                    <h2 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-white sm:text-3xl">SQL Schema & Reporting Specialist</h2>
                    <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400 sm:text-base">
                      This specialized interface uses Agility Reporting best practices. Ask about table grains, business key joins, and SQL patterns for the AgilitySQL schema.
                    </p>
                    <div className="mt-8 grid gap-4 sm:grid-cols-2">
                       {reportingPrompts.map((prompt) => (
                         <button
                           key={prompt.label}
                           onClick={() => setDraft(prompt.label)}
                           className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:border-blue-500/40 hover:bg-blue-50/50 dark:border-slate-800 dark:bg-slate-900/50 dark:hover:bg-blue-900/20"
                         >
                           <span className="text-xl">{prompt.icon}</span>
                           <span className="text-sm font-medium">{prompt.label}</span>
                         </button>
                       ))}
                    </div>
                  </div>
                  
                  <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 dark:border-amber-500/30 dark:bg-amber-900/10">
                    <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-400">⚠️ Reporting Rules</h3>
                    <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-amber-700 dark:text-amber-300">
                      <li>Never join on <code>prrowid</code>; always use business keys.</li>
                      <li>Be mindful of the grain (header vs detail).</li>
                      <li>Tables like <code>item_activity</code> need date filters for performance.</li>
                    </ul>
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
                  />
                ))
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <MessageInput
            onSend={handleSendMessage}
            disabled={isLoading}
            value={draft}
            onChange={setDraft}
            inputRef={inputRef}
            onUploadImage={(file) => conversationService.uploadImage(file, activeConversationId)}
          />
        </div>
      </section>
    </main>
  );
}
