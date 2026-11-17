export type ModelTier = "flash" | "pro" | "advance";
export type TaskType = "chat" | "images" | "video" | "code" | "audio" | "rag";
export type FrameworkBackend = "numpy" | "pytorch" | "tensorflow" | "keras" | "hybrid";
export type NavSection = "overview" | "analytics" | "studio" | "settings";
export type SettingsTab = "general" | "engine" | "keys" | "agents" | "billing" | "profiles" | "transactions" | "all";

export interface NeuralDiagnostics {
  backend_used: string;
  frameworks_invoked: string[];
  device: string;
  parameter_count: number;
  latent_norm: number;
  confidence_score: number;
  latency_ms: number;
}

export interface GenerationResponse {
  request_id: string;
  model_id: string;
  tier: ModelTier;
  task: TaskType;
  conversation_id?: number | null;
  conversation_title?: string;
  text?: string | null;
  code?: string | null;
  language?: string | null;
  artifact_url?: string | null;
  preview_base64?: string | null;
  mime_type?: string | null;
  credits_used: number;
  tokens_input: number;
  tokens_output: number;
  diagnostics: NeuralDiagnostics;
  extra?: Record<string, unknown>;
  quota?: QuotaStatus;
  created_at: string;
}

export interface ConversationMessageItem {
  id: number;
  role: "system" | "user" | "assistant";
  content: string;
  task: TaskType;
  tier: ModelTier;
  backend_used: string;
  code: string;
  language: string;
  artifact_url: string;
  preview_base64: string;
  mime_type: string;
  credits_used: number;
  latency_ms: number;
  intent: string;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  task: TaskType;
  tier: ModelTier;
  system_prompt: string;
  message_count: number;
  last_message: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ConversationMessageItem[];
}

export interface TrainingSampleInput {
  prompt: string;
  response: string;
  intent: string;
  task: TaskType;
}

export interface TrainingRequestPayload {
  tier: ModelTier;
  backend?: FrameworkBackend | null;
  epochs: number;
  learning_rate?: number;
  include_builtin_dataset?: boolean;
  include_recent_conversations?: boolean;
  samples?: TrainingSampleInput[];
  save_checkpoint?: boolean;
}

export interface BackendTrainingStats {
  backend: string;
  device: string;
  epochs: number;
  initial_loss: number;
  final_loss: number;
  accuracy: number;
  samples_seen: number;
  parameter_count: number;
  checkpoint_path?: string | null;
}

export interface TrainingResult {
  training_id: string;
  tier: ModelTier;
  model_id: string;
  dataset_size: number;
  learned_intents: string[];
  backends_trained: BackendTrainingStats[];
  checkpoint_path?: string | null;
  duration_ms: number;
  completed_at: string;
}

export interface TrainingStatusResponse {
  trained: boolean;
  dataset_size: number;
  learned_intents: string[];
  checkpoint_dir: string;
  last_training: TrainingResult | null;
}

export interface AllTiersTrainingResult {
  training_id: string;
  dataset_size: number;
  learned_intents: string[];
  tier_results: TrainingResult[];
  total_duration_ms: number;
  completed_at: string;
}

export interface TrainingSampleRecordItem {
  id: number;
  prompt: string;
  response: string;
  intent: string;
  task: TaskType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TrainingRunItem {
  id: number;
  training_id: string;
  username?: string;
  scope: "single" | "all";
  tier: ModelTier;
  backend: string;
  epochs: number;
  learning_rate: number;
  dataset_size: number;
  learned_intents: string[];
  backends_trained: BackendTrainingStats[];
  duration_ms: number;
  status: string;
  created_at: string;
}

export interface EvaluationResult {
  prompt: string;
  tier: ModelTier;
  predicted_intent: string;
  intent_confidence: number;
  expected_intent?: string | null;
  intent_matched?: boolean | null;
  matched_sample_prompt?: string | null;
  matched_sample_score: number;
  confidence_score: number;
  frameworks_invoked: string[];
  generated_preview: string;
}

export interface ModelSummary {
  model_id: string;
  tier: ModelTier;
  display_name: string;
  description: string;
  primary_backend: FrameworkBackend;
  supported_tasks: TaskType[];
  credit_cost: Record<TaskType, number>;
  hidden_dim: number;
  num_layers: number;
  max_tokens: number;
  parameter_estimate: number;
}

export interface UserProfile {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  avatar?: string;
  bio?: string;
  role_title?: string;
  organization?: string;
  default_tier?: ModelTier;
  default_task?: TaskType;
  default_system_prompt?: string;
  is_superuser?: boolean;
  is_staff?: boolean;
  date_joined?: string;
  remaining_credits?: number;
  plan_name?: string;
  conversation_count?: number;
  updated_at?: string;
}

export interface SecretKeyItem {
  id: number;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at?: string | null;
  secret_key?: string;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
}

export interface QuotaStatus {
  total_credits: number;
  used_credits: number;
  remaining_credits: number;
  daily_requests: number;
  max_daily_requests: number;
  last_reset_date: string;
}

export type PaymentMethod = "bkash" | "nagad" | "rocket" | "upay";

export interface MfsPaymentPayload {
  currency?: "USD" | "BDT";
  amount_bdt?: string;
  payment_method?: PaymentMethod | "";
  tnxid?: string;
}

export interface BillingPlan {
  id: number;
  name: string;
  slug: string;
  monthly_price_usd: string;
  monthly_price_bdt?: string;
  bdt_rate?: string;
  monthly_credits: number;
  daily_request_limit: number;
  allowed_tiers: string[];
  description: string;
}

export interface SubscriptionInfo {
  id: number;
  plan: BillingPlan;
  status: string;
  started_at: string;
  renews_at: string | null;
}

export interface TransactionItem {
  id: number;
  reference_id: string;
  tx_type: string;
  currency?: string;
  amount_usd: string;
  amount_bdt?: string;
  payment_method?: string;
  tnxid?: string;
  credits_delta: number;
  balance_after: number;
  model_tier: string;
  task_type: string;
  description: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface InvoiceItem {
  id: number;
  invoice_number: string;
  plan_name: string;
  currency?: string;
  amount_usd: string;
  amount_bdt?: string;
  payment_method?: string;
  tnxid?: string;
  credits_granted: number;
  status: string;
  created_at: string;
}

export interface SubscribeResponse {
  subscription: SubscriptionInfo;
  invoice: InvoiceItem;
  quota: QuotaStatus;
}

export interface TopUpResponse {
  remaining_credits: number;
  quota: QuotaStatus;
  transaction: TransactionItem;
}

export interface MfsPaymentRequestItem {
  id: number;
  username: string;
  kind: "credits" | "plan";
  plan_slug: string;
  plan_name: string;
  credits_requested: number;
  currency: string;
  amount_usd: string;
  amount_bdt: string;
  payment_method: string;
  tnxid: string;
  sender_number: string;
  status: "pending" | "approved" | "rejected";
  admin_note: string;
  reviewed_by_username: string;
  reviewed_at: string | null;
  invoice_number: string;
  created_at: string;
}

export interface CheckoutReceipt {
  kind: "credits" | "plan";
  reference: string;
  title: string;
  amountUsd: string;
  amountBdt?: string;
  paymentMethod?: string;
  tnxid?: string;
  creditsAdded: number;
  balanceAfter: number;
  verified: boolean;
  pending?: boolean;
  dailyLimit?: number;
}

export interface CheckoutActionResult {
  ok: boolean;
  error?: string;
  receipt?: CheckoutReceipt;
}

export interface AgentProfile {
  id: number;
  name: string;
  slug: string;
  system_prompt: string;
  default_tier: ModelTier;
  default_task: TaskType;
  tools_enabled: string[];
  is_public: boolean;
}

export interface AgentRunItem {
  id: number;
  agent: number | null;
  agent_name: string;
  prompt: string;
  selected_tier: ModelTier;
  selected_task: TaskType;
  response_text: string;
  artifact_url: string;
  status: string;
  credits_used: number;
  latency_ms: number;
  created_at: string;
}

export interface BackendHealthInfo {
  available: boolean;
  version: string;
  device: string;
  details: Record<string, unknown>;
}

export interface FrontierLibraryInfo {
  available: boolean;
  version: string | null;
  error?: string;
}

export interface EngineHealthResponse {
  status: string;
  django: string;
  fastapi: {
    status: string;
    service?: string;
    version?: string;
    backends?: Record<string, BackendHealthInfo>;
    frontier_libraries?: Record<string, FrontierLibraryInfo>;
    detail?: string;
  };
}

export interface AnalyticsSummary {
  total_requests: number;
  used_credits: number;
  remaining_credits: number;
  total_credits: number;
  daily_requests: number;
  max_daily_requests: number;
  avg_latency_ms: number;
  total_conversations: number;
  total_messages: number;
  total_agent_runs: number;
}

export interface TierBreakdownItem {
  tier: ModelTier;
  requests: number;
  credits: number;
  avg_latency_ms: number;
}

export interface TaskBreakdownItem {
  task: TaskType;
  requests: number;
  credits: number;
  avg_latency_ms: number;
}

export interface DailyActivityItem {
  date: string;
  label: string;
  requests: number;
  credits: number;
  avg_latency_ms: number;
}

export interface UsageLogItem {
  id: number;
  model_tier: string;
  task_type: string;
  credits_consumed: number;
  latency_ms: number;
  endpoint: string;
  created_at: string;
}

export interface DashboardAnalytics {
  summary: AnalyticsSummary;
  by_tier: TierBreakdownItem[];
  by_task: TaskBreakdownItem[];
  daily_activity: DailyActivityItem[];
  recent_logs: UsageLogItem[];
}

export interface DashboardData {
  user: UserProfile;
  quota: QuotaStatus;
  subscription: SubscriptionInfo | null;
  recent_transactions: TransactionItem[];
  models: ModelSummary[];
  fastapi_base_url: string;
}
