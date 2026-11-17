/**
 * Lightweight fetch API client for Django control plane + Djoser JWT auth.
 */
window.AIModelAPI = (() => {
  const TOKEN_KEY = "ai_model_access_token";
  const REFRESH_KEY = "ai_model_refresh_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setTokens(access, refresh) {
    if (access) localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  }

  function clearTokens() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }

  async function request(url, options = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, { ...options, headers });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text };
    }

    if (!res.ok) {
      const msg = (data && (data.detail || JSON.stringify(data))) || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  return {
    getToken,
    setTokens,
    clearTokens,
    login: async (username, password) => {
      const data = await request("/api/auth/jwt/create/", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setTokens(data.access, data.refresh);
      return data;
    },
    register: (username, email, password) =>
      request("/api/auth/users/", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      }),
    getHealth: () => request("/api/v1/health/"),
    getModels: () => request("/api/v1/models/"),
    getDashboard: () => request("/api/v1/dashboard/"),
    getProfile: () => request("/api/v1/profile/"),
    updateProfile: (payload) =>
      request("/api/v1/profile/", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    getProfiles: () => request("/api/v1/profiles/"),
    changePassword: (payload) =>
      request("/api/auth/users/set_password/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getPlans: () => request("/api/billing/plans/"),
    subscribePlan: (plan_slug, payment) =>
      request("/api/billing/subscribe/", {
        method: "POST",
        body: JSON.stringify({ plan_slug, ...(payment || {}) }),
      }),
    topupCredits: (credits, payment) =>
      request("/api/transactions/topup/", {
        method: "POST",
        body: JSON.stringify({ credits, ...(payment || {}) }),
      }),
    getInvoices: () => request("/api/billing/invoices/"),
    getTransactions: () => request("/api/transactions/"),
    verifyAccount: (reconcile = true) =>
      request("/api/v1/verify/", {
        method: "POST",
        body: JSON.stringify({ reconcile }),
      }),
    verifyCheckout: (payload) =>
      request("/api/billing/checkout/verify/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getAdminOverview: () => request("/api/billing/admin/overview/"),
    approveMfsRequest: (id, note = "") =>
      request(`/api/billing/admin/mfs-requests/${id}/approve/`, {
        method: "POST",
        body: JSON.stringify({ admin_note: note }),
      }),
    rejectMfsRequest: (id, note = "") =>
      request(`/api/billing/admin/mfs-requests/${id}/reject/`, {
        method: "POST",
        body: JSON.stringify({ admin_note: note }),
      }),
    adminGrantCredits: (payload) =>
      request("/api/billing/admin/grant-credits/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    adminClearBalance: (payload) =>
      request("/api/billing/admin/clear-balance/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    adminSwitchPlan: (payload) =>
      request("/api/billing/admin/switch-plan/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getSecretKeys: () => request("/api/v1/keys/"),
    createSecretKey: (name) =>
      request("/api/v1/keys/", {
        method: "POST",
        body: JSON.stringify({ name: name || "Default API Key" }),
      }),
    toggleSecretKey: (id, is_active) =>
      request(`/api/v1/keys/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_active }),
      }),
    revokeSecretKey: (id) =>
      request(`/api/v1/keys/${id}/`, {
        method: "DELETE",
      }),
    getAgents: () => request("/api/agent/profiles/"),
    createAgent: (payload) =>
      request("/api/agent/profiles/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getAgentRuns: () => request("/api/agent/runs/"),
    executeAgent: (payload) =>
      request("/api/agent/execute/", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    generate: (task, payload) =>
      request(`/api/v1/generate/${task}/`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    getConversations: () => request("/api/v1/conversations/"),
    getConversation: (id) => request(`/api/v1/conversations/${id}/`),
    createConversation: (payload) =>
      request("/api/v1/conversations/", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    deleteConversation: (id) =>
      request(`/api/v1/conversations/${id}/`, {
        method: "DELETE",
      }),
    getTrainingStatus: () => request("/api/v1/train/"),
    trainEngine: (payload) =>
      request("/api/v1/train/", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    trainAll: (payload) =>
      request("/api/v1/train/all/", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    getTrainingHistory: (limit = 25) =>
      request(`/api/v1/train/history/?limit=${encodeURIComponent(limit)}`),
    getTrainingSamples: () => request("/api/v1/train/samples/"),
    createTrainingSample: (payload) =>
      request("/api/v1/train/samples/", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    deleteTrainingSample: (id) =>
      request(`/api/v1/train/samples/${id}/`, {
        method: "DELETE",
      }),
    evaluateTraining: (payload) =>
      request("/api/v1/train/evaluate/", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    getTrainingCheckpoints: () => request("/api/v1/train/checkpoints/"),
    resetTraining: () =>
      request("/api/v1/train/reset/", {
        method: "POST",
        body: JSON.stringify({}),
      }),
  };
})();

