const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
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
    let errorMessage = `Request failed: ${response.status}`;
    try {
      const errorPayload = await response.json();
      if (typeof errorPayload?.detail === 'string' && errorPayload.detail.trim()) {
        errorMessage = errorPayload.detail.trim();
      }
    } catch {
      // Fall back to the HTTP status message when the error body is not JSON.
    }
    throw new Error(errorMessage);
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

  async create(payload = {}) {
    const fallback = {
      id: crypto.randomUUID(),
      title: 'New conversation',
      folderId: payload.folderId || null,
      createdAt: now(),
      updatedAt: now(),
      messages: [],
    };

    try {
      return await request('/conversations', { method: 'POST', body: JSON.stringify(payload) });
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

  async ask(question, conversationId, mode = 'default') {
    const response = await request('/ask', {
      method: 'POST',
      body: JSON.stringify({ question, conversationId, mode }),
    });

    return response;
  },

  async currentUser() {
    try {
      return await request('/users/me');
    } catch {
      return {
        identity: 'local',
        trainingConsent: false,
      };
    }
  },

  async trackEngagement(payload) {
    try {
      return await request('/engagement', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch {
      return { ok: false };
    }
  },

  async submitCorrection(conversationId, messageId, correctedAnswer, notes = '') {
    return request('/feedback/corrections', {
      method: 'POST',
      body: JSON.stringify({
        conversationId,
        messageId,
        correctedAnswer,
        notes,
      }),
    });
  },

  async getAdminMetrics(token) {
    return request('/admin/metrics', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  async listFolders() {
    try {
      return await request('/folders');
    } catch {
      return [];
    }
  },

  async createFolder(title) {
    return request('/folders', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  },

  async updateFolder(folderId, payload) {
    return request(`/folders/${folderId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async deleteFolder(folderId) {
    return request(`/folders/${folderId}`, {
      method: 'DELETE',
    });
  },

  async getPromptStarters() {
    try {
      return await request('/prompt-starters');
    } catch {
      return {
        starters: [],
        trendingQuestions: [],
        relatedTopics: [],
      };
    }
  },

  async uploadImage(file, conversationId) {
    const formData = new FormData();
    formData.append('file', file);
    if (conversationId) formData.append('conversationId', conversationId);

    const response = await fetch(`${API_BASE}/uploads/images`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Image upload failed: ${response.status}`);
    }

    return response.json();
  },
};
