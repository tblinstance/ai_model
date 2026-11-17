import { useEffect, useState } from "react";
import {
  Bot,
  Check,
  Cpu,
  CreditCard,
  KeyRound,
  LayoutGrid,
  Lock,
  Moon,
  PanelLeft,
  Receipt,
  Settings,
  Sparkles,
  Sun,
  UserCheck,
} from "lucide-react";
import {
  AgentProfile,
  AgentRunItem,
  BillingPlan,
  CheckoutActionResult,
  InvoiceItem,
  MfsPaymentPayload,
  MfsPaymentRequestItem,
  ModelSummary,
  ModelTier,
  QuotaStatus,
  SecretKeyItem,
  SettingsTab,
  SubscriptionInfo,
  TaskType,
  TransactionItem,
  UserProfile,
} from "../types/ai";
import { AgentsView } from "./AgentsView";
import { ApiKeysView } from "./ApiKeysView";
import { BillingQuotaView } from "./BillingQuotaView";
import { EngineStatusView } from "./EngineStatusView";
import { ProfilesView } from "./ProfilesView";
import { TransactionsView } from "./TransactionsView";

export const SETTINGS_TABS: Array<{ id: SettingsTab; label: string; icon: typeof Settings }> = [
  { id: "general", label: "General", icon: Settings },
  { id: "engine", label: "Model Tiers", icon: Cpu },
  { id: "keys", label: "API Keys", icon: KeyRound },
  { id: "agents", label: "Agents", icon: Bot },
  { id: "billing", label: "Billing & Quota", icon: CreditCard },
  { id: "profiles", label: "Profiles", icon: UserCheck },
  { id: "transactions", label: "Transactions", icon: Receipt },
  { id: "all", label: "All", icon: LayoutGrid },
];

interface SettingsViewProps {
  activeTab: SettingsTab;
  onSelectTab: (tab: SettingsTab) => void;
  authenticated: boolean;
  onOpenAuth: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  sidebarCollapsed: boolean;
  onToggleSidebarCollapsed: () => void;
  activeTier: ModelTier;
  activeTask: TaskType;
  onSelectTier: (tier: ModelTier) => void;
  onSelectTask: (task: TaskType) => void;
  user: UserProfile | null;
  profiles: UserProfile[];
  secretKeys: SecretKeyItem[];
  onSaveProfile: (payload: Partial<UserProfile>) => Promise<void>;
  onCreateSecretKey: (name: string) => Promise<SecretKeyItem | null>;
  onToggleSecretKey: (id: number, nextActive: boolean) => Promise<void>;
  onRevokeSecretKey: (id: number) => Promise<void>;
  onChangePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  models: ModelSummary[];
  agents: AgentProfile[];
  agentRuns: AgentRunItem[];
  onCreateAgent: (payload: {
    name: string;
    system_prompt: string;
    default_tier: ModelTier;
    default_task: TaskType;
  }) => Promise<void>;
  onExecuteAgent: (agentId: number, prompt: string, tier: ModelTier) => Promise<void>;
  plans: BillingPlan[];
  subscription: SubscriptionInfo | null;
  quota: QuotaStatus | null;
  invoices?: InvoiceItem[];
  mfsRequests?: MfsPaymentRequestItem[];
  onSubscribe: (slug: string, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult>;
  onTopup: (credits: number, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult>;
  onOpenCheckout?: () => void;
  onOpenCheckoutPlan?: (planSlug: string) => void;
  transactions: TransactionItem[];
}

export function SettingsView({
  activeTab,
  onSelectTab,
  authenticated,
  onOpenAuth,
  theme,
  onToggleTheme,
  sidebarCollapsed,
  onToggleSidebarCollapsed,
  activeTier,
  activeTask,
  onSelectTier,
  onSelectTask,
  user,
  profiles,
  secretKeys,
  onSaveProfile,
  onCreateSecretKey,
  onToggleSecretKey,
  onRevokeSecretKey,
  onChangePassword,
  models,
  agents,
  agentRuns,
  onCreateAgent,
  onExecuteAgent,
  plans,
  subscription,
  quota,
  invoices = [],
  mfsRequests = [],
  onSubscribe,
  onTopup,
  onOpenCheckout,
  onOpenCheckoutPlan,
  transactions,
}: SettingsViewProps) {
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState(user?.default_system_prompt || "");
  const [savingDefaults, setSavingDefaults] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    setDefaultSystemPrompt(user?.default_system_prompt || "");
  }, [user?.default_system_prompt]);

  const handleSaveEngineDefaults = async (e: React.FormEvent) => {
    e.preventDefault();
    if (savingDefaults) return;
    setSavingDefaults(true);
    try {
      await onSaveProfile({
        default_tier: activeTier,
        default_task: activeTask,
        default_system_prompt: defaultSystemPrompt.trim(),
      });
    } finally {
      setSavingDefaults(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }
    setSavingPassword(true);
    try {
      await onChangePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } finally {
      setSavingPassword(false);
    }
  };

  const showSection = (tab: Exclude<SettingsTab, "all">) => activeTab === tab || activeTab === "all";

  return (
    <div className="space-y-4">
      {/* Unified Settings Sub-Navigation */}
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-2 flex flex-wrap gap-1.5 shadow-xs dark:shadow-none">
        {SETTINGS_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onSelectTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                active
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/70"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {showSection("general") && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
              <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
                <span>Appearance &amp; Workspace Layout</span>
              </h2>

              <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-white">Color Theme</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    Currently using {theme === "dark" ? "Dark Mode" : "Light Mode"}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onToggleTheme}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5"
                >
                  {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                  <span>{theme === "dark" ? "Switch to Light" : "Switch to Dark"}</span>
                </button>
              </div>

              <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-white">Desktop Sidenav</div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400">
                    {sidebarCollapsed ? "Collapsed icon bar" : "Expanded full sidebar"}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onToggleSidebarCollapsed}
                  className="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-semibold flex items-center gap-1.5"
                >
                  <PanelLeft className="w-3.5 h-3.5" />
                  <span>{sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}</span>
                </button>
              </div>
            </div>

            <form
              onSubmit={handleSaveEngineDefaults}
              className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none"
            >
              <div className="flex items-center justify-between">
                <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <span>AI Defaults &amp; Engine Mode</span>
                </h2>
                <button
                  type="submit"
                  disabled={savingDefaults}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>{savingDefaults ? "Saving..." : "Save Defaults"}</span>
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Active Tier</label>
                  <select
                    value={activeTier}
                    onChange={(e) => onSelectTier(e.target.value as ModelTier)}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100"
                  >
                    <option value="flash">tblinc Flash</option>
                    <option value="pro">tblinc Pro</option>
                    <option value="advance">tblinc Advance</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">Studio Mode</label>
                  <select
                    value={activeTask}
                    onChange={(e) => onSelectTask(e.target.value as TaskType)}
                    className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100"
                  >
                    <option value="chat">AI Chat</option>
                    <option value="images">Create Images</option>
                    <option value="video">Create Videos</option>
                    <option value="code">Create Code</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-slate-500 dark:text-slate-400 mb-1">
                  Default System Instruction
                </label>
                <input
                  type="text"
                  value={defaultSystemPrompt}
                  onChange={(e) => setDefaultSystemPrompt(e.target.value)}
                  placeholder="Optional system prompt stored in your profile..."
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
                />
              </div>
            </form>
          </div>

          <form
            onSubmit={handlePasswordSubmit}
            className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none"
          >
            <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span>Change Password</span>
            </h2>

            {passwordError && (
              <div className="rounded-lg bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/40 px-3 py-1.5 text-xs text-rose-700 dark:text-rose-200">
                {passwordError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Current password"
                className="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
              />
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="New password (8+ chars)"
                className="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
              />
              <input
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                className="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={savingPassword}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold disabled:opacity-50"
              >
                {savingPassword ? "Updating..." : "Update Password"}
              </button>
            </div>
          </form>
        </div>
      )}

      {showSection("engine") && (
        <EngineStatusView
          models={models}
          activeTier={activeTier}
          onSelectTier={onSelectTier}
        />
      )}

      {showSection("keys") && (
        <ApiKeysView
          secretKeys={secretKeys}
          authenticated={authenticated}
          onCreateKey={onCreateSecretKey}
          onToggleKey={onToggleSecretKey}
          onDeleteKey={onRevokeSecretKey}
          onOpenAuth={onOpenAuth}
        />
      )}

      {showSection("agents") && (
        <AgentsView
          agents={agents}
          runs={agentRuns}
          activeTier={activeTier}
          authenticated={authenticated}
          onCreateAgent={onCreateAgent}
          onExecuteAgent={onExecuteAgent}
          onOpenAuth={onOpenAuth}
        />
      )}

      {showSection("billing") && (
        <BillingQuotaView
          user={user}
          plans={plans}
          subscription={subscription}
          quota={quota}
          invoices={invoices}
          mfsRequests={mfsRequests}
          activeTier={activeTier}
          authenticated={authenticated}
          onSubscribe={onSubscribe}
          onTopup={onTopup}
          onOpenCheckout={onOpenCheckout}
          onOpenCheckoutPlan={onOpenCheckoutPlan}
          onUpdateProfile={(email) => onSaveProfile({ email })}
          onOpenAuth={onOpenAuth}
        />
      )}

      {showSection("profiles") && (
        <ProfilesView
          user={user}
          profiles={profiles}
          onSaveProfile={onSaveProfile}
        />
      )}

      {showSection("transactions") && (
        <TransactionsView
          transactions={transactions}
          authenticated={authenticated}
          onOpenAuth={onOpenAuth}
        />
      )}
    </div>
  );
}
