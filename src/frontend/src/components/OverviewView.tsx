import {
  ArrowRight,
  BarChart3,
  Bot,
  Check,
  Code2,
  Coins,
  Cpu,
  CreditCard,
  Film,
  Image as ImageIcon,
  KeyRound,
  Layers,
  MessageSquare,
  Receipt,
  Sparkles,
  UserCheck,
  Zap,
} from "lucide-react";
import {
  creditsToBdtNumber,
  creditsToUsdNumber,
  formatBdt,
  formatCreditsBdtUsd,
  formatUsd,
} from "../services/payment";
import {
  ConversationSummary,
  DashboardAnalytics,
  ModelSummary,
  ModelTier,
  NavSection,
  QuotaStatus,
  SettingsTab,
  SubscriptionInfo,
  TaskType,
  UserProfile,
} from "../types/ai";

interface OverviewViewProps {
  user: UserProfile | null;
  activeTier: ModelTier;
  onSelectTier: (tier: ModelTier) => void;
  models: ModelSummary[];
  quota: QuotaStatus | null;
  subscription: SubscriptionInfo | null;
  analytics: DashboardAnalytics | null;
  conversations: ConversationSummary[];
  onQuickTask: (task: TaskType) => void;
  onOpenConversation: (id: number) => void;
  onNavigateSection: (section: NavSection) => void;
  onOpenSettingsTab: (tab: SettingsTab) => void;
}

const QUICK_TASKS: Array<{
  id: TaskType;
  label: string;
  caption: string;
  icon: typeof MessageSquare;
  accent: string;
}> = [
  {
    id: "chat",
    label: "tblinc Chat",
    caption: "Multi-turn reasoning, Q&A, and research assistance",
    icon: MessageSquare,
    accent: "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-500/15",
  },
  {
    id: "images",
    label: "tblinc Images",
    caption: "Generate custom visual concepts and artwork",
    icon: ImageIcon,
    accent: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/15",
  },
  {
    id: "video",
    label: "tblinc Video",
    caption: "Synthesize short motion clips and previews",
    icon: Film,
    accent: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/15",
  },
  {
    id: "code",
    label: "tblinc Code",
    caption: "Generate clean snippets, APIs, and scripts",
    icon: Code2,
    accent: "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-500/15",
  },
];

const TIER_ICONS: Record<ModelTier, typeof Zap> = {
  flash: Zap,
  pro: Cpu,
  advance: Sparkles,
};

export function OverviewView({
  user,
  activeTier,
  onSelectTier,
  models,
  quota,
  subscription,
  analytics,
  conversations,
  onQuickTask,
  onOpenConversation,
  onNavigateSection,
  onOpenSettingsTab,
}: OverviewViewProps) {
  const displayName = user?.display_name?.trim() || (user?.username ? `@${user.username}` : "Workspace");
  const planName = subscription?.plan?.name || "Starter";
  const summary = analytics?.summary;
  const creditPct = quota
    ? Math.min(100, Math.round((quota.remaining_credits / Math.max(1, quota.total_credits)) * 100))
    : 0;

  return (
    <div className="space-y-4">
      {/* Top Welcome & Quota Summary (sm) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        <div className="lg:col-span-8 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between gap-3 shadow-xs dark:shadow-none">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30">
                  {planName} Plan
                </span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-md bg-cyan-50 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-500/30">
                  Active: tblinc {activeTier}
                </span>
              </div>
              <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white">
                Welcome back, {displayName}
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                Choose a model tier, launch AI Studio across Chat, Images, Videos, or Code, and monitor your workspace activity.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onNavigateSection("studio")}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Open AI Studio</span>
              </button>
              <button
                type="button"
                onClick={() => onNavigateSection("analytics")}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200/80 dark:border-slate-800/80 text-xs">
            <div className="rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 p-2.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Total Requests</div>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                {(summary?.total_requests ?? 0).toLocaleString()}
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 p-2.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Saved Threads</div>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                {(summary?.total_conversations ?? conversations.length).toLocaleString()}
              </div>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 p-2.5">
              <div className="text-[11px] text-slate-500 dark:text-slate-400">Messages</div>
              <div className="font-display font-bold text-base text-slate-900 dark:text-white">
                {(summary?.total_messages ?? 0).toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Compact Quota Card (sm) */}
        <div className="lg:col-span-4 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col justify-between gap-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between">
            <span className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
              <Coins className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              Credits &amp; Quota
            </span>
            <button
              type="button"
              onClick={() => onOpenSettingsTab("billing")}
              className="text-[11px] font-semibold text-indigo-600 dark:text-cyan-400 hover:underline"
            >
              Manage Plan
            </button>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-2xl font-bold text-slate-900 dark:text-white">
                {formatBdt(creditsToBdtNumber(quota?.remaining_credits))}
              </span>
              <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                {formatUsd(creditsToUsdNumber(quota?.remaining_credits))} USD / {formatCreditsBdtUsd(quota?.total_credits, { compact: true })}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-indigo-600 transition-all duration-300"
                style={{ width: `${creditPct}%` }}
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200/80 dark:border-slate-800/80">
            <span>Daily Calls</span>
            <span className="text-slate-800 dark:text-slate-200 font-semibold">
              {quota?.daily_requests ?? 0} / {quota?.max_daily_requests ?? 250}
            </span>
          </div>
        </div>
      </div>

      {/* Quick Launch tblinc AI Models */}
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>tblinc AI Models Workspace</span>
          </h3>
          <span className="text-[11px] text-slate-500 dark:text-slate-400">
            Select a creation mode to start immediately
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {QUICK_TASKS.map((task) => {
            const Icon = task.icon;
            return (
              <button
                key={task.id}
                type="button"
                onClick={() => onQuickTask(task.id)}
                className="text-left rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/50 p-3.5 space-y-2 transition group"
              >
                <div className="flex items-center justify-between">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${task.accent}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-cyan-500 transition-transform group-hover:translate-x-0.5" />
                </div>
                <div>
                  <div className="font-display font-semibold text-xs text-slate-900 dark:text-white">
                    {task.label}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                    {task.caption}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Model Tier Selection */}
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span>Model Tiers</span>
          </h3>
          <button
            type="button"
            onClick={() => onOpenSettingsTab("engine")}
            className="text-[11px] font-semibold text-indigo-600 dark:text-cyan-400 hover:underline"
          >
            Compare All Tiers
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {models.map((m) => {
            const Icon = TIER_ICONS[m.tier] || Cpu;
            const isActive = m.tier === activeTier;
            return (
              <div
                key={m.model_id}
                className={`rounded-xl bg-slate-50 dark:bg-slate-950/75 border p-3.5 flex flex-col justify-between gap-3 ${
                  isActive
                    ? "border-cyan-500/70 dark:border-cyan-500/60 shadow-sm shadow-cyan-500/10"
                    : "border-slate-200 dark:border-slate-800"
                }`}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                      <Icon className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
                      {m.display_name}
                    </span>
                    {isActive && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        Active
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400">{m.description}</p>
                  <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                    Context: {m.max_tokens} tokens · Chat: {formatCreditsBdtUsd(m.credit_cost?.chat ?? 1, { compact: true })}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onSelectTier(m.tier)}
                  className={`w-full py-1.5 rounded-lg text-xs font-semibold transition ${
                    isActive
                      ? "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-500/40"
                      : "bg-indigo-600 hover:bg-indigo-500 text-white"
                  }`}
                >
                  {isActive ? "Active Tier" : `Select ${m.display_name}`}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom: Recent Conversations & Settings Shortcuts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
              Recent Conversations
            </h3>
            <button
              type="button"
              onClick={() => onQuickTask("chat")}
              className="text-[11px] font-semibold text-indigo-600 dark:text-cyan-400 hover:underline"
            >
              New Chat
            </button>
          </div>
          <div className="space-y-1.5">
            {conversations.slice(0, 5).map((conv) => (
              <button
                key={conv.id}
                type="button"
                onClick={() => onOpenConversation(conv.id)}
                className="w-full text-left rounded-lg bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/40 p-2.5 transition flex items-center justify-between gap-2"
              >
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">{conv.title}</div>
                  <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 uppercase">
                    {conv.tier} · {conv.task} · {conv.message_count} msgs
                  </div>
                </div>
                <span className="text-[11px] font-semibold text-indigo-600 dark:text-cyan-400 shrink-0">Resume</span>
              </button>
            ))}
            {!conversations.length && (
              <p className="text-xs text-slate-500 py-5 text-center">
                No saved threads yet. Start a prompt in AI Studio to create one.
              </p>
            )}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-2.5 shadow-xs dark:shadow-none">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
            Workspace Shortcuts
          </h3>
          <div className="grid grid-cols-2 gap-2.5">
            {(
              [
                { tab: "keys", label: "API Keys", desc: "Access credentials", icon: KeyRound },
                { tab: "agents", label: "Agents", desc: "Custom assistants", icon: Bot },
                { tab: "billing", label: "Billing & Quota", desc: "Plans & credits", icon: CreditCard },
                { tab: "profiles", label: "Profiles", desc: "Account settings", icon: UserCheck },
                { tab: "transactions", label: "Transactions", desc: "Usage history", icon: Receipt },
              ] as const
            ).map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.tab}
                  type="button"
                  onClick={() => onOpenSettingsTab(item.tab)}
                  className="text-left rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 hover:border-indigo-500/40 p-3 space-y-1 transition"
                >
                  <Icon className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
                  <div className="text-xs font-semibold text-slate-900 dark:text-white">{item.label}</div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">{item.desc}</div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

