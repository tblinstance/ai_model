import { useCallback, useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { aiService } from "./services/aiService";
import { formatCreditsBdtUsd } from "./services/payment";
import {
  clearAuthTokens,
  extractErrorMessage,
  getAccessToken,
} from "./services/http";
import {
  AgentProfile,
  AgentRunItem,
  BillingPlan,
  CheckoutActionResult,
  ConversationDetail,
  ConversationSummary,
  DashboardAnalytics,
  EngineHealthResponse,
  GenerationResponse,
  InvoiceItem,
  MfsPaymentPayload,
  MfsPaymentRequestItem,
  ModelSummary,
  ModelTier,
  NavSection,
  NotificationItem,
  QuotaStatus,
  SecretKeyItem,
  SettingsTab,
  SubscriptionInfo,
  TaskType,
  TransactionItem,
  UserProfile,
} from "./types/ai";
import { AuthModal, AuthMode } from "./components/AuthModal";
import { CheckoutModal } from "./components/CheckoutModal";
import { DashboardAnalyticsView } from "./components/DashboardAnalyticsView";
import { Header } from "./components/Header";
import { OverviewView } from "./components/OverviewView";
import { SETTINGS_TABS, SettingsView } from "./components/SettingsView";
import { NAV_ITEMS, Sidebar, TASK_NAV_ITEMS } from "./components/Sidebar";
import { StudioView } from "./components/StudioView";

const ACTIVE_TIER_STORAGE_KEY = "ai_model_active_tier";
const SIDEBAR_COLLAPSED_STORAGE_KEY = "sidebarCollapsed";
const THEME_STORAGE_KEY = "theme";

function readInitialTier(): ModelTier {
  const saved = localStorage.getItem(ACTIVE_TIER_STORAGE_KEY);
  if (saved === "flash" || saved === "pro" || saved === "advance") {
    return saved;
  }
  return "flash";
}

function readInitialSidebarCollapsed(): boolean {
  return localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === "true";
}

function readInitialTheme(): "light" | "dark" {
  return localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark";
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(getAccessToken()));
  const [activeSection, setActiveSection] = useState<NavSection>("overview");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("general");
  const [activeTier, setActiveTier] = useState<ModelTier>(readInitialTier);
  const [activeTask, setActiveTask] = useState<TaskType>("chat");
  const [theme, setTheme] = useState<"light" | "dark">(readInitialTheme);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next: "light" | "dark" = prev === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_STORAGE_KEY, next);
      document.documentElement.classList.toggle("dark", next === "dark");
      document.documentElement.setAttribute("data-theme", next);
      return next;
    });
  }, []);

  const activateProjectTier = useCallback((tier: ModelTier) => {
    setActiveTier(tier);
    localStorage.setItem(ACTIVE_TIER_STORAGE_KEY, tier);
  }, []);

  const [user, setUser] = useState<UserProfile | null>(null);
  const [profiles, setProfiles] = useState<UserProfile[]>([]);
  const [secretKeys, setSecretKeys] = useState<SecretKeyItem[]>([]);
  const [quota, setQuota] = useState<QuotaStatus | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [plans, setPlans] = useState<BillingPlan[]>([]);
  const [models, setModels] = useState<ModelSummary[]>([]);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [mfsRequests, setMfsRequests] = useState<MfsPaymentRequestItem[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRunItem[]>([]);
  const [health, setHealth] = useState<EngineHealthResponse | null>(null);
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);

  const [outputs, setOutputs] = useState<GenerationResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [notice, setNotice] = useState<string>("");
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  const pushNotification = useCallback((id: string, title: string, message: string, read = false) => {
    setNotifications((prev) => {
      if (prev.some((item) => item.id === id)) return prev;
      const entry: NotificationItem = {
        id,
        title,
        message,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        read,
      };
      return [entry, ...prev].slice(0, 20);
    });
  }, []);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [checkoutMode, setCheckoutMode] = useState<"credits" | "plans">("credits");
  const [checkoutPlanSlug, setCheckoutPlanSlug] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authError, setAuthError] = useState<string>("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(readInitialSidebarCollapsed);

  const handleToggleSidebar = useCallback(() => {
    if (window.innerWidth < 1024) {
      setSidebarOpen((prev) => !prev);
      return;
    }
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const expandDesktopSidebar = useCallback(() => {
    setSidebarCollapsed(false);
    localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, "false");
  }, []);

  const activeTaskLabel = TASK_NAV_ITEMS.find((t) => t.id === activeTask)?.label || "AI Chat";
  const activeSettingsTabLabel =
    SETTINGS_TABS.find((t) => t.id === settingsTab)?.label || "General";
  const sectionTitle =
    activeSection === "studio"
      ? `AI Studio · ${activeTaskLabel}`
      : activeSection === "settings"
        ? `Settings · ${activeSettingsTabLabel}`
        : NAV_ITEMS.find((item) => item.id === activeSection)?.label || "AI Studio";

  const openAuthModal = (mode: AuthMode = "login") => {
    setAuthMode(mode);
    setAuthError("");
    setAuthModalOpen(true);
  };

  const loadPublic = useCallback(async () => {
    if (!getAccessToken()) return;
    const [healthRes, modelsRes, plansRes] = await Promise.allSettled([
      aiService.getHealth(),
      aiService.getModels(),
      aiService.getPlans(),
    ]);
    if (healthRes.status === "fulfilled") setHealth(healthRes.value);
    if (modelsRes.status === "fulfilled") setModels(modelsRes.value);
    if (plansRes.status === "fulfilled") setPlans(plansRes.value);
  }, []);

  const loadPrivate = useCallback(async () => {
    if (!getAccessToken()) return;
    try {
      const dash = await aiService.getDashboard();
      setUser(dash.user);
      setQuota(dash.quota);
      setSubscription(dash.subscription);
      setTransactions(dash.recent_transactions);
      if (dash.models.length) setModels(dash.models);
      for (const tx of dash.recent_transactions.slice(0, 5)) {
        pushNotification(
          `tx-${tx.reference_id}`,
          `${formatCreditsBdtUsd(tx.credits_delta, { signed: true, compact: true })} · ${tx.tx_type}`,
          tx.description || "Account transaction",
          true
        );
      }
      if (dash.quota && dash.quota.remaining_credits <= 25) {
        pushNotification(
          `low-credits-${dash.quota.remaining_credits}`,
          "Low Balance",
          `Only ${formatCreditsBdtUsd(dash.quota.remaining_credits)} left. Top up via Checkout.`,
          false
        );
      }

      const [agRes, runRes, convRes, profRes, analRes, keyRes, invRes, mfsRes, healthRes] = await Promise.allSettled([
        aiService.getAgents(),
        aiService.getAgentRuns(),
        aiService.getConversations(),
        aiService.getProfiles(),
        aiService.getAnalytics(),
        aiService.getSecretKeys(),
        aiService.getInvoices(),
        aiService.getMfsRequests(),
        aiService.getHealth(),
      ]);
      if (agRes.status === "fulfilled") setAgents(agRes.value);
      if (runRes.status === "fulfilled") setAgentRuns(runRes.value);
      if (convRes.status === "fulfilled") {
        setConversations(convRes.value);
      }
      if (profRes.status === "fulfilled") {
        setProfiles(profRes.value);
      }
      if (analRes.status === "fulfilled") {
        setAnalytics(analRes.value);
      }
      if (keyRes.status === "fulfilled") {
        setSecretKeys(keyRes.value);
      }
      if (invRes.status === "fulfilled") {
        setInvoices(invRes.value);
      }
      if (mfsRes.status === "fulfilled") {
        setMfsRequests(mfsRes.value);
      }
      if (healthRes.status === "fulfilled") {
        setHealth(healthRes.value);
      }
    } catch (err) {
      const msg = extractErrorMessage(err);
      if (msg.toLowerCase().includes("token") || msg.includes("401")) {
        clearAuthTokens();
        setAuthenticated(false);
        setUser(null);
      }
    }
  }, []);

  useEffect(() => {
    void loadPublic();
    void loadPrivate();
  }, [loadPublic, loadPrivate]);

  useEffect(() => {
    if (!authenticated) return;
    const isOnline = health?.fastapi?.status === "ok";
    const intervalMs = isOnline ? 20000 : 3000;
    const timer = window.setInterval(() => {
      void aiService.getHealth().then(setHealth).catch(() => undefined);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [authenticated, health?.fastapi?.status]);

  useEffect(() => {
    if (!authenticated || !mfsRequests.some((r) => r.status === "pending")) return;
    const timer = window.setInterval(() => {
      void loadPrivate();
    }, 10000);
    return () => window.clearInterval(timer);
  }, [authenticated, mfsRequests, loadPrivate]);

  const handleSelectConversation = async (id: number) => {
    setError("");
    try {
      const detail = await aiService.getConversation(id);
      setActiveConversation(detail);
      setActiveTask(detail.task);
      setActiveSection("studio");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleNewConversation = async () => {
    if (!authenticated) {
      openAuthModal("login");
      return;
    }
    setError("");
    setOutputs([]);
    setActiveSection("studio");
    try {
      const created = await aiService.createConversation({
        title: "New Conversation",
        task: activeTask,
        tier: activeTier,
      });
      setActiveConversation(created);
      setConversations((prev) => [created, ...prev.filter((c) => c.id !== created.id)]);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleDeleteConversation = async (id: number) => {
    setError("");
    try {
      await aiService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversation?.id === id) {
        setActiveConversation(null);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleSelectTaskLink = (task: TaskType) => {
    setActiveTask(task);
    setActiveSection("studio");
  };

  const handleAuth = async (
    mode: AuthMode,
    username: string,
    email: string,
    password: string
  ) => {
    setError("");
    setAuthError("");
    try {
      if (mode === "register") {
        await aiService.register(username, email, password);
      }
      await aiService.login(username, password);
      setAuthenticated(true);
      setAuthModalOpen(false);
      setNotice(mode === "register" ? `Account created! Signed in as @${username}` : `Signed in as @${username}`);
      await Promise.all([loadPublic(), loadPrivate()]);
    } catch (err) {
      setAuthError(extractErrorMessage(err));
    }
  };

  const handleLogout = () => {
    clearAuthTokens();
    setAuthenticated(false);
    setUser(null);
    setProfiles([]);
    setSecretKeys([]);
    setNotifications([]);
    setQuota(null);
    setSubscription(null);
    setPlans([]);
    setModels([]);
    setHealth(null);
    setAnalytics(null);
    setTransactions([]);
    setInvoices([]);
    setMfsRequests([]);
    setAgents([]);
    setAgentRuns([]);
    setConversations([]);
    setActiveConversation(null);
    setOutputs([]);
  };

  const handleGenerate = async (
    prompt: string,
    language?: string,
    systemPrompt?: string,
    metadata?: Record<string, unknown>,
    taskOverride?: TaskType,
    durationSeconds?: number
  ) => {
    if (!authenticated) {
      openAuthModal("login");
      return;
    }
    const targetTask = taskOverride || activeTask;
    setLoading(true);
    setError("");
    try {
      const res = await aiService.generate(targetTask, {
        prompt,
        tier: activeTier,
        language,
        system_prompt: systemPrompt,
        conversation_id: activeConversation?.id ?? null,
        ...(durationSeconds ? { duration_seconds: durationSeconds } : {}),
        ...(metadata ? { metadata } : {}),
      });
      setOutputs((prev) => [res, ...prev]);
      if (res.quota) setQuota(res.quota);
      if (res.conversation_id) {
        const detail = await aiService.getConversation(res.conversation_id);
        setActiveConversation(detail);
        setConversations((prev) => [detail, ...prev.filter((c) => c.id !== detail.id)]);
      }
      await loadPrivate();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async (payload: {
    name: string;
    system_prompt: string;
    default_tier: ModelTier;
    default_task: TaskType;
  }) => {
    setError("");
    try {
      await aiService.createAgent(payload);
      setNotice(`Agent '${payload.name}' created.`);
      await loadPrivate();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleExecuteAgent = async (agentId: number, prompt: string, tier: ModelTier) => {
    setError("");
    try {
      const res = await aiService.executeAgent({
        agent_id: agentId,
        prompt,
        tier,
      });
      setOutputs((prev) => [res.result, ...prev]);
      setNotice("Agent run completed.");
      await loadPrivate();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleSubscribe = async (slug: string, payment?: MfsPaymentPayload): Promise<CheckoutActionResult> => {
    setError("");
    try {
      if (payment?.payment_method && payment?.tnxid) {
        const res = await aiService.submitMfsRequest({
          kind: "plan",
          plan_slug: slug,
          payment_method: payment.payment_method,
          tnxid: payment.tnxid,
          amount_bdt: payment.amount_bdt,
        });
        setMfsRequests((prev) => [res.request, ...prev]);
        setNotice(
          `Submitted ${res.request.plan_name} request #${res.request.id} (${res.request.payment_method.toUpperCase()} ${res.request.tnxid}) for Admin approval.`
        );
        pushNotification(
          `mfs-plan-${res.request.id}`,
          "Payment Pending Approval",
          `${res.request.plan_name} · ${res.request.payment_method.toUpperCase()} TrxID ${res.request.tnxid}`
        );
        void loadPrivate();
        return {
          ok: true,
          receipt: {
            kind: "plan",
            reference: `MFS-#${res.request.id}`,
            title: `${res.request.plan_name} Monthly Plan`,
            amountUsd: String(res.request.amount_usd),
            amountBdt: res.request.amount_bdt,
            paymentMethod: res.request.payment_method,
            tnxid: res.request.tnxid,
            creditsAdded: res.request.credits_requested,
            balanceAfter: quota?.remaining_credits ?? 0,
            verified: false,
            pending: true,
          },
        };
      }

      const res = await aiService.subscribePlan(slug, payment);
      setSubscription(res.subscription);
      setQuota(res.quota);
      setInvoices((prev) => [res.invoice, ...prev]);
      const planName = res.subscription?.plan?.name || slug;
      setNotice(`Activated plan '${planName}' (Invoice ${res.invoice.invoice_number}).`);
      pushNotification(
        `sub-${res.invoice.invoice_number}`,
        "Plan Activated",
        `Switched to ${planName} · Balance: ${formatCreditsBdtUsd(res.quota.remaining_credits)}.`
      );
      void loadPrivate();
      return {
        ok: true,
        receipt: {
          kind: "plan",
          reference: res.invoice.invoice_number,
          title: `${planName} Monthly Plan`,
          amountUsd: String(res.invoice.amount_usd),
          amountBdt: res.invoice.amount_bdt,
          paymentMethod: res.invoice.payment_method,
          tnxid: res.invoice.tnxid,
          creditsAdded: res.invoice.credits_granted,
          balanceAfter: res.quota.remaining_credits,
          verified: true,
          dailyLimit: res.subscription.plan.daily_request_limit,
        },
      };
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      return { ok: false, error: msg };
    }
  };

  const handleTopup = async (credits: number, payment?: MfsPaymentPayload): Promise<CheckoutActionResult> => {
    setError("");
    try {
      const res = await aiService.submitMfsRequest({
        kind: "credits",
        credits,
        payment_method: payment?.payment_method || "bkash",
        tnxid: payment?.tnxid || "",
        amount_bdt: payment?.amount_bdt,
      });
      setMfsRequests((prev) => [res.request, ...prev]);
      setNotice(
        `Submitted ${formatCreditsBdtUsd(credits)} checkout (${res.request.payment_method.toUpperCase()} ${res.request.tnxid}) — awaiting Admin approval.`
      );
      pushNotification(
        `mfs-cr-${res.request.id}`,
        "Payment Pending Approval",
        `${formatCreditsBdtUsd(credits, { signed: true, compact: true })} · ${res.request.payment_method.toUpperCase()} TrxID ${res.request.tnxid}`
      );
      void loadPrivate();
      return {
        ok: true,
        receipt: {
          kind: "credits",
          reference: `MFS-#${res.request.id}`,
          title: `${credits.toLocaleString()} AI Credits Pack`,
          amountUsd: String(res.request.amount_usd),
          amountBdt: res.request.amount_bdt,
          paymentMethod: res.request.payment_method,
          tnxid: res.request.tnxid,
          creditsAdded: res.request.credits_requested,
          balanceAfter: quota?.remaining_credits ?? 0,
          verified: false,
          pending: true,
        },
      };
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      return { ok: false, error: msg };
    }
  };

  const handleUpdateProfile = async (payload: Partial<UserProfile> | string) => {
    setError("");
    try {
      const body = typeof payload === "string" ? { email: payload } : payload;
      const updated = await aiService.updateProfile(body);
      setUser((prev) => (prev ? { ...prev, ...updated } : updated));
      if (updated.default_tier) activateProjectTier(updated.default_tier);
      if (updated.default_task) setActiveTask(updated.default_task);
      setNotice(`Profile saved (@${updated.username}).`);
      await loadPrivate();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleChangePassword = async (currentPassword: string, newPassword: string) => {
    setError("");
    try {
      await aiService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setNotice("Password updated successfully.");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleCreateSecretKey = async (name: string): Promise<SecretKeyItem | null> => {
    setError("");
    try {
      const created = await aiService.createSecretKey(name);
      setSecretKeys((prev) => [created, ...prev]);
      setNotice(`Created API key '${created.name}'. Copy it before leaving this page.`);
      pushNotification(`key-${created.id}`, "API Key Created", `Generated key '${created.name}'.`);
      return created;
    } catch (err) {
      setError(extractErrorMessage(err));
      return null;
    }
  };

  const handleToggleSecretKey = async (id: number, nextActive: boolean) => {
    setError("");
    try {
      const updated = await aiService.toggleSecretKey(id, nextActive);
      setSecretKeys((prev) => prev.map((k) => (k.id === id ? updated : k)));
      setNotice(`API key ${nextActive ? "enabled" : "paused"}.`);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleRevokeSecretKey = async (id: number) => {
    setError("");
    try {
      await aiService.revokeSecretKey(id);
      setSecretKeys((prev) => prev.filter((k) => k.id !== id));
      setNotice("API key revoked.");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  return (
    <div className="min-h-screen lg:h-screen lg:overflow-hidden w-full flex">
      <Sidebar
        activeSection={activeSection}
        activeTask={activeTask}
        onSelectSection={setActiveSection}
        onSelectTaskLink={handleSelectTaskLink}
        activeTier={activeTier}
        onSelectTier={(tier) => {
          if (!authenticated) {
            openAuthModal("login");
            return;
          }
          activateProjectTier(tier);
        }}
        models={models}
        quota={quota}
        authenticated={authenticated}
        open={sidebarOpen}
        collapsed={sidebarCollapsed}
        onClose={() => setSidebarOpen(false)}
        onExpandSidebar={expandDesktopSidebar}
        onOpenAuth={openAuthModal}
        user={user}
        onOpenProfile={() => {
          setSettingsTab("profiles");
          setActiveSection("settings");
        }}
        onOpenBilling={() => {
          setSettingsTab("billing");
          setActiveSection("settings");
        }}
        onOpenSettings={() => {
          setSettingsTab("general");
          setActiveSection("settings");
        }}
        onLogout={handleLogout}
      />

      <div className="flex-1 flex flex-col min-w-0 lg:h-screen lg:overflow-hidden">
        <Header
          sectionTitle={sectionTitle}
          activeTier={activeTier}
          theme={theme}
          onToggleTheme={toggleTheme}
          health={health}
          user={user}
          quota={quota}
          notifications={notifications}
          onMarkAllRead={() => setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))}
          onClearNotifications={() => setNotifications([])}
          authenticated={authenticated}
          onToggleSidebar={handleToggleSidebar}
          onOpenAuth={openAuthModal}
          onOpenProfile={() => {
            setSettingsTab("profiles");
            setActiveSection("settings");
          }}
          onOpenBilling={() => {
            setSettingsTab("billing");
            setActiveSection("settings");
          }}
          onOpenCheckout={() => {
            setCheckoutMode("credits");
            setCheckoutPlanSlug(null);
            setCheckoutOpen(true);
          }}
          onOpenKeys={() => {
            setSettingsTab("keys");
            setActiveSection("settings");
          }}
          onOpenSettings={() => {
            setSettingsTab("general");
            setActiveSection("settings");
          }}
          onRefreshHealth={() => void loadPublic()}
          onLogout={handleLogout}
        />

        <main className="flex-1 min-w-0 w-full overflow-y-auto p-4 sm:p-6 space-y-5">
          {error && (
            <div className="rounded-xl bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/40 px-4 py-2.5 text-xs text-rose-700 dark:text-rose-200 flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError("")} className="underline">
                Dismiss
              </button>
            </div>
          )}

          {notice && (
            <div className="rounded-xl bg-emerald-50 dark:bg-emerald-500/15 border border-emerald-200 dark:border-emerald-500/40 px-4 py-2.5 text-xs text-emerald-700 dark:text-emerald-200 flex items-center justify-between">
              <span>{notice}</span>
              <button onClick={() => setNotice("")} className="underline">
                Dismiss
              </button>
            </div>
          )}

          {!authenticated ? (
            <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center space-y-3 shadow-xs dark:shadow-none">
              <div className="w-11 h-11 rounded-2xl bg-indigo-50 dark:bg-indigo-500/15 text-indigo-600 dark:text-cyan-400 mx-auto flex items-center justify-center">
                <Lock className="w-5 h-5" />
              </div>
              <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">
                Authentication Required
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto">
                Sign in to access {sectionTitle}, switch model tiers, create AI chats, images, videos, code, and manage your workspace.
              </p>
              <div className="flex items-center justify-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => openAuthModal("login")}
                  className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-xs font-semibold"
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => openAuthModal("register")}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                >
                  Sign Up
                </button>
              </div>
            </div>
          ) : (
            <>
              {activeSection === "overview" && (
                <OverviewView
                  user={user}
                  activeTier={activeTier}
                  onSelectTier={activateProjectTier}
                  models={models}
                  quota={quota}
                  subscription={subscription}
                  analytics={analytics}
                  conversations={conversations}
                  onQuickTask={(task) => {
                    setActiveTask(task);
                    setActiveSection("studio");
                  }}
                  onOpenConversation={(id) => void handleSelectConversation(id)}
                  onNavigateSection={setActiveSection}
                  onOpenSettingsTab={(tab) => {
                    setSettingsTab(tab);
                    setActiveSection("settings");
                  }}
                />
              )}

              {activeSection === "analytics" && (
                <DashboardAnalyticsView
                  analytics={analytics}
                  conversations={conversations}
                  activeTier={activeTier}
                  onQuickTask={(task) => {
                    setActiveTask(task);
                    setActiveSection("studio");
                  }}
                  onOpenConversation={(id) => void handleSelectConversation(id)}
                />
              )}

              {activeSection === "studio" && (
                <StudioView
                  activeTier={activeTier}
                  activeTask={activeTask}
                  onSelectTask={setActiveTask}
                  models={models}
                  outputs={outputs}
                  conversations={conversations}
                  activeConversation={activeConversation}
                  loading={loading}
                  onSelectConversation={handleSelectConversation}
                  onNewConversation={handleNewConversation}
                  onDeleteConversation={handleDeleteConversation}
                  onGenerate={handleGenerate}
                />
              )}

              {activeSection === "settings" && (
                <SettingsView
                  activeTab={settingsTab}
                  onSelectTab={setSettingsTab}
                  authenticated={authenticated}
                  onOpenAuth={() => openAuthModal("login")}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  sidebarCollapsed={sidebarCollapsed}
                  onToggleSidebarCollapsed={() => {
                    setSidebarCollapsed((prev) => {
                      const next = !prev;
                      localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(next));
                      return next;
                    });
                  }}
                  activeTier={activeTier}
                  activeTask={activeTask}
                  onSelectTier={activateProjectTier}
                  onSelectTask={setActiveTask}
                  user={user}
                  profiles={profiles}
                  secretKeys={secretKeys}
                  onSaveProfile={handleUpdateProfile}
                  onCreateSecretKey={handleCreateSecretKey}
                  onToggleSecretKey={handleToggleSecretKey}
                  onRevokeSecretKey={handleRevokeSecretKey}
                  onChangePassword={handleChangePassword}
                  models={models}
                  agents={agents}
                  agentRuns={agentRuns}
                  onCreateAgent={handleCreateAgent}
                  onExecuteAgent={handleExecuteAgent}
                  plans={plans}
                  subscription={subscription}
                  quota={quota}
                  invoices={invoices}
                  mfsRequests={mfsRequests}
                  onSubscribe={handleSubscribe}
                  onTopup={handleTopup}
                  onOpenCheckout={() => {
                    setCheckoutMode("credits");
                    setCheckoutPlanSlug(null);
                    setCheckoutOpen(true);
                  }}
                  onOpenCheckoutPlan={(slug) => {
                    setCheckoutMode("plans");
                    setCheckoutPlanSlug(slug);
                    setCheckoutOpen(true);
                  }}
                  transactions={transactions}
                />
              )}
            </>
          )}
        </main>
      </div>

      <AuthModal
        open={authModalOpen}
        mode={authMode}
        error={authError}
        onModeChange={setAuthMode}
        onClearError={() => setAuthError("")}
        onClose={() => setAuthModalOpen(false)}
        onSubmit={handleAuth}
      />

      <CheckoutModal
        open={checkoutOpen}
        initialMode={checkoutMode}
        initialPlanSlug={checkoutPlanSlug}
        user={user}
        quota={quota}
        subscription={subscription}
        plans={plans}
        onClose={() => setCheckoutOpen(false)}
        onTopup={handleTopup}
        onSubscribe={handleSubscribe}
        onOpenBilling={() => {
          setSettingsTab("billing");
          setActiveSection("settings");
        }}
      />
    </div>
  );
}
