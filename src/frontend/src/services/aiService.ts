import {
  AgentProfile,
  AgentRunItem,
  BillingPlan,
  ConversationDetail,
  ConversationSummary,
  DashboardAnalytics,
  DashboardData,
  EngineHealthResponse,
  FrameworkBackend,
  GenerationResponse,
  InvoiceItem,
  MfsPaymentPayload,
  MfsPaymentRequestItem,
  ModelSummary,
  ModelTier,
  SecretKeyItem,
  SubscribeResponse,
  TaskType,
  TopUpResponse,
  TransactionItem,
  UserProfile,
} from "../types/ai";
import { djangoHttp, setAuthTokens } from "./http";

export const aiService = {
  async login(username: string, password: string): Promise<void> {
    const { data } = await djangoHttp.post<{ access: string; refresh: string }>(
      "/api/auth/jwt/create/",
      { username, password }
    );
    setAuthTokens(data.access, data.refresh);
  },

  async register(username: string, email: string, password: string): Promise<void> {
    await djangoHttp.post("/api/auth/users/", { username, email, password });
  },

  async getHealth(): Promise<EngineHealthResponse> {
    const { data } = await djangoHttp.get<EngineHealthResponse>("/api/v1/health/");
    return data;
  },

  async getModels(): Promise<ModelSummary[]> {
    const { data } = await djangoHttp.get<ModelSummary[]>("/api/v1/models/");
    return data;
  },

  async getDashboard(): Promise<DashboardData> {
    const { data } = await djangoHttp.get<DashboardData>("/api/v1/dashboard/");
    return data;
  },

  async getAnalytics(): Promise<DashboardAnalytics> {
    const { data } = await djangoHttp.get<DashboardAnalytics>("/api/v1/analytics/");
    return data;
  },

  async getProfile(): Promise<UserProfile> {
    const { data } = await djangoHttp.get<UserProfile>("/api/v1/profile/");
    return data;
  },

  async updateProfile(payload: Partial<UserProfile>): Promise<UserProfile> {
    const { data } = await djangoHttp.patch<UserProfile>("/api/v1/profile/", payload);
    return data;
  },

  async getProfiles(): Promise<UserProfile[]> {
    const { data } = await djangoHttp.get<UserProfile[]>("/api/v1/profiles/");
    return data;
  },

  async getSecretKeys(): Promise<SecretKeyItem[]> {
    const { data } = await djangoHttp.get<SecretKeyItem[]>("/api/v1/keys/");
    return data;
  },

  async createSecretKey(name: string): Promise<SecretKeyItem> {
    const { data } = await djangoHttp.post<SecretKeyItem>("/api/v1/keys/", { name });
    return data;
  },

  async toggleSecretKey(id: number, isActive: boolean): Promise<SecretKeyItem> {
    const { data } = await djangoHttp.patch<SecretKeyItem>(`/api/v1/keys/${id}/`, {
      is_active: isActive,
    });
    return data;
  },

  async revokeSecretKey(id: number): Promise<void> {
    await djangoHttp.delete(`/api/v1/keys/${id}/`);
  },

  async changePassword(payload: { current_password: string; new_password: string }): Promise<void> {
    await djangoHttp.post("/api/auth/users/set_password/", payload);
  },

  async getConversations(): Promise<ConversationSummary[]> {
    const { data } = await djangoHttp.get<ConversationSummary[]>("/api/v1/conversations/");
    return data;
  },

  async getConversation(id: number): Promise<ConversationDetail> {
    const { data } = await djangoHttp.get<ConversationDetail>(`/api/v1/conversations/${id}/`);
    return data;
  },

  async createConversation(payload?: {
    title?: string;
    task?: TaskType;
    tier?: ModelTier;
    system_prompt?: string;
  }): Promise<ConversationDetail> {
    const { data } = await djangoHttp.post<ConversationDetail>(
      "/api/v1/conversations/",
      payload || {}
    );
    return data;
  },

  async deleteConversation(id: number): Promise<void> {
    await djangoHttp.delete(`/api/v1/conversations/${id}/`);
  },

  async generate(
    task: TaskType,
    payload: {
      prompt: string;
      tier: ModelTier;
      backend?: FrameworkBackend;
      language?: string;
      system_prompt?: string;
      conversation_id?: number | null;
      duration_seconds?: number;
      metadata?: Record<string, unknown>;
    }
  ): Promise<GenerationResponse> {
    const { data } = await djangoHttp.post<GenerationResponse>(
      `/api/v1/generate/${task}/`,
      payload
    );
    return data;
  },

  async getPlans(): Promise<BillingPlan[]> {
    const { data } = await djangoHttp.get<BillingPlan[]>("/api/billing/plans/");
    return data;
  },

  async subscribePlan(planSlug: string, payment?: MfsPaymentPayload): Promise<SubscribeResponse> {
    const { data } = await djangoHttp.post<SubscribeResponse>("/api/billing/subscribe/", {
      plan_slug: planSlug,
      ...(payment || {}),
    });
    return data;
  },

  async topupCredits(credits: number, payment?: MfsPaymentPayload): Promise<TopUpResponse> {
    const { data } = await djangoHttp.post<TopUpResponse>("/api/transactions/topup/", {
      credits,
      ...(payment || {}),
    });
    return data;
  },

  async getInvoices(): Promise<InvoiceItem[]> {
    const { data } = await djangoHttp.get<InvoiceItem[]>("/api/billing/invoices/");
    return data;
  },

  async getMfsRequests(): Promise<MfsPaymentRequestItem[]> {
    const { data } = await djangoHttp.get<MfsPaymentRequestItem[]>("/api/billing/mfs-requests/");
    return data;
  },

  async submitMfsRequest(payload: {
    kind: "credits" | "plan";
    credits?: number;
    plan_slug?: string;
    payment_method: string;
    tnxid: string;
    amount_bdt?: string;
    sender_number?: string;
  }): Promise<{ checkout_status: string; request: MfsPaymentRequestItem }> {
    const { data } = await djangoHttp.post<{ checkout_status: string; request: MfsPaymentRequestItem }>(
      "/api/billing/mfs-requests/",
      payload
    );
    return data;
  },

  async getTransactions(): Promise<TransactionItem[]> {
    const { data } = await djangoHttp.get<TransactionItem[]>("/api/transactions/");
    return data;
  },

  async getAgents(): Promise<AgentProfile[]> {
    const { data } = await djangoHttp.get<AgentProfile[]>("/api/agent/profiles/");
    return data;
  },

  async createAgent(payload: {
    name: string;
    system_prompt: string;
    default_tier: ModelTier;
    default_task: TaskType;
  }): Promise<AgentProfile> {
    const { data } = await djangoHttp.post<AgentProfile>("/api/agent/profiles/", payload);
    return data;
  },

  async getAgentRuns(): Promise<AgentRunItem[]> {
    const { data } = await djangoHttp.get<AgentRunItem[]>("/api/agent/runs/");
    return data;
  },

  async executeAgent(payload: {
    agent_id?: number;
    prompt: string;
    tier: ModelTier;
    task?: TaskType;
    backend?: FrameworkBackend;
  }): Promise<{ run: AgentRunItem; result: GenerationResponse; remaining_credits: number }> {
    const { data } = await djangoHttp.post("/api/agent/execute/", payload);
    return data;
  },

  async transcribeAudio(audio_base64: string, language?: string): Promise<{ text: string; language: string; success: boolean }> {
    const { data } = await djangoHttp.post("/api/v1/audio/transcribe/", { audio_base64, language });
    return data;
  },

  async analyzeAudio(audio_base64: string): Promise<Record<string, unknown>> {
    const { data } = await djangoHttp.post("/api/v1/audio/analyze/", { audio_base64 });
    return data;
  },

  async scrapeRagUrl(url: string): Promise<{ url: string; title: string; indexed_chunks: number; success: boolean }> {
    const { data } = await djangoHttp.post("/api/v1/rag/scrape/", { url });
    return data;
  },
};
