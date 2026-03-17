const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'agility-ai-conversations';

const now = () => new Date().toISOString();

function loadLocalConversations() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveLocalConversations(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export const conversationService = {
  async list() {
    try {
      return await request('/conversations');
    } catch {
      return loadLocalConversations();
    }
  },

  async create() {
    const fallback = {
      id: crypto.randomUUID(),
      title: 'New conversation',
      createdAt: now(),
      updatedAt: now(),
      messages: [],
    };

    try {
      return await request('/conversations', { method: 'POST', body: JSON.stringify({}) });
    } catch {
      const existing = loadLocalConversations();
      const updated = [fallback, ...existing];
      saveLocalConversations(updated);
      return fallback;
    }
  },

  async update(conversationId, payload) {
    try {
      return await request(`/conversations/${conversationId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      });
    } catch {
      const existing = loadLocalConversations();
      const updated = existing.map((c) => (c.id === conversationId ? { ...c, ...payload, updatedAt: now() } : c));
      saveLocalConversations(updated);
      return updated.find((c) => c.id === conversationId);
    }
  },

  async remove(conversationId) {
    try {
      await request(`/conversations/${conversationId}`, { method: 'DELETE' });
      return;
    } catch {
      const existing = loadLocalConversations();
      saveLocalConversations(existing.filter((c) => c.id !== conversationId));
    }
  },

  async appendMessage(conversationId, message) {
    try {
      return await request('/messages', {
        method: 'POST',
        body: JSON.stringify({ conversationId, ...message }),
      });
    } catch {
      const existing = loadLocalConversations();
      const updated = existing.map((c) => {
        if (c.id !== conversationId) return c;
        return {
          ...c,
          updatedAt: now(),
          messages: [...(c.messages || []), message],
        };
      });
      saveLocalConversations(updated);
      return message;
    }
  },

  async ask(question) {
    const response = await request('/ask', {
      method: 'POST',
      body: JSON.stringify({ question }),
    });

    return response.answer;
  },
};
