/**
 * Portal URL path resolver & builder for deep-linking across Django routes.
 */
window.AIModelPortalRoute = (() => {
  const VALID_SECTIONS = ["overview", "studio", "training", "settings", "admin"];
  const VALID_TASKS = ["chat", "images", "video", "code"];
  const VALID_TABS = ["general", "keys", "agents", "billing", "profiles", "transactions", "all"];
  const VALID_ADMIN_TABS = ["mfs", "users", "invoices", "transactions"];
  const AUTH_PATHS = ["/", "/login", "/login/", "/register", "/register/"];
  const ADMIN_PATH_ALIASES = {
    mfs: "mfs",
    "admin-control": "mfs",
    users: "users",
    invoices: "invoices",
    billings: "invoices",
    "admin-transactions": "transactions",
  };
  const TAB_ALIASES = {
    billing: "billing",
    keys: "keys",
    "api-keys": "keys",
    agents: "agents",
    profiles: "profiles",
    transactions: "transactions",
  };

  function normalizeChoice(val, allowed, fallback) {
    const clean = String(val || "").trim().toLowerCase();
    return allowed.includes(clean) ? clean : fallback;
  }

  function isAuthPath(pathname) {
    const raw = String(pathname || "/").toLowerCase();
    return AUTH_PATHS.includes(raw);
  }

  function sanitizeNextPath(candidate) {
    const raw = String(candidate || "").trim();
    if (!raw.startsWith("/") || raw.startsWith("//")) return "/control/";
    if (isAuthPath(raw.split("?")[0])) return "/control/";
    if (/^\/(control|overview|studio|training|settings|billing|keys|api-keys|agents|profiles|transactions|mfs|users|invoices|billings|admin-transactions|admin-control|admin)(\/|$)/i.test(raw)) {
      return raw.endsWith("/") ? raw : `${raw}/`;
    }
    return "/control/";
  }

  function parsePath(pathname, serverRoute) {
    const baseTask = normalizeChoice(serverRoute && serverRoute.task, VALID_TASKS, "chat");
    const baseTab = normalizeChoice(serverRoute && serverRoute.settingsTab, VALID_TABS, "general");
    const baseAdminTab = normalizeChoice(serverRoute && serverRoute.adminTab, VALID_ADMIN_TABS, "mfs");
    const rawServerSection = String((serverRoute && serverRoute.section) || "").trim().toLowerCase();
    const baseSection = rawServerSection === "auth"
      ? "overview"
      : normalizeChoice(rawServerSection, VALID_SECTIONS, "overview");

    const rawPath = String(pathname || "/");
    if (isAuthPath(rawPath)) {
      return {
        section: "overview",
        task: baseTask,
        settingsTab: baseTab,
        adminTab: baseAdminTab,
        isAuth: true,
        authMode: rawPath.toLowerCase().startsWith("/register") || (serverRoute && serverRoute.mode === "register")
          ? "register"
          : "login",
      };
    }

    const stripped = rawPath.replace(/^\/control(?=\/|$)/i, "");
    const parts = stripped
      .replace(/^\/+|\/+$/g, "")
      .split("/")
      .filter(Boolean)
      .map((p) => p.toLowerCase());

    if (!parts.length || parts[0] === "overview") {
      return {
        section: "overview",
        task: baseTask,
        settingsTab: baseTab,
        adminTab: baseAdminTab,
        isAuth: false,
        authMode: "login",
      };
    }
    if (parts[0] === "studio") {
      return {
        section: "studio",
        task: normalizeChoice(parts[1], VALID_TASKS, baseTask),
        settingsTab: baseTab,
        adminTab: baseAdminTab,
        isAuth: false,
        authMode: "login",
      };
    }
    if (parts[0] === "settings") {
      return {
        section: "settings",
        task: baseTask,
        settingsTab: normalizeChoice(parts[1], VALID_TABS, baseTab),
        adminTab: baseAdminTab,
        isAuth: false,
        authMode: "login",
      };
    }
    if (parts[0] === "admin") {
      return {
        section: "admin",
        task: baseTask,
        settingsTab: baseTab,
        adminTab: normalizeChoice(parts[1], VALID_ADMIN_TABS, baseAdminTab),
        isAuth: false,
        authMode: "login",
      };
    }
    if (Object.prototype.hasOwnProperty.call(ADMIN_PATH_ALIASES, parts[0])) {
      return {
        section: "admin",
        task: baseTask,
        settingsTab: baseTab,
        adminTab: ADMIN_PATH_ALIASES[parts[0]],
        isAuth: false,
        authMode: "login",
      };
    }
    if (parts[0] === "training") {
      return {
        section: "training",
        task: baseTask,
        settingsTab: baseTab,
        adminTab: baseAdminTab,
        isAuth: false,
        authMode: "login",
      };
    }
    if (Object.prototype.hasOwnProperty.call(TAB_ALIASES, parts[0])) {
      return {
        section: "settings",
        task: baseTask,
        settingsTab: TAB_ALIASES[parts[0]],
        adminTab: baseAdminTab,
        isAuth: false,
        authMode: "login",
      };
    }
    return {
      section: baseSection,
      task: baseTask,
      settingsTab: baseTab,
      adminTab: baseAdminTab,
      isAuth: false,
      authMode: "login",
    };
  }

  function buildPath(section, task, settingsTab, currentPathname, adminTab) {
    const cur = String(currentPathname || "/control/");
    const prefix = /^\/control(\/|$)/i.test(cur) || isAuthPath(cur) ? "/control" : "";
    if (section === "admin") {
      const normalizedAdminTab = normalizeChoice(adminTab, VALID_ADMIN_TABS, "mfs");
      if (normalizedAdminTab === "users") return `${prefix}/users/`;
      if (normalizedAdminTab === "invoices") return `${prefix}/invoices/`;
      if (normalizedAdminTab === "transactions") return `${prefix}/admin-transactions/`;
      return `${prefix}/mfs/`;
    }
    if (section === "studio") {
      return `${prefix}/studio/${normalizeChoice(task, VALID_TASKS, "chat")}/`;
    }
    if (section === "training") {
      return `${prefix}/training/`;
    }
    if (section === "settings") {
      return `${prefix}/settings/${normalizeChoice(settingsTab, VALID_TABS, "general")}/`;
    }
    if (prefix) {
      return "/control/";
    }
    return cur === "/" ? "/" : "/overview/";
  }

  return { parsePath, buildPath, isAuthPath, sanitizeNextPath };
})();

/**
 * Reactive Vue 3 store for the Django Vue CDN control center.
 */
window.createAIModelStore = () => {
  const { reactive } = Vue;
  const savedTier = localStorage.getItem("ai_model_backend_active_tier");
  const initialTier = savedTier === "flash" || savedTier === "pro" || savedTier === "advance" ? savedTier : "flash";
  const pathname = window.location.pathname || "/";
  const searchParams = new URLSearchParams(window.location.search || "");
  const initialRoute = window.AIModelPortalRoute.parsePath(
    pathname,
    window.__PORTAL_ROUTE__ || null
  );
  const initialPostAuthPath = window.AIModelPortalRoute.isAuthPath(pathname)
    ? window.AIModelPortalRoute.sanitizeNextPath(searchParams.get("next"))
    : window.AIModelPortalRoute.sanitizeNextPath(pathname);
  return reactive({
    authenticated: Boolean(window.AIModelAPI.getToken()),
    user: null,
    profiles: [],
    secretKeys: [],
    revealedSecretKey: "",
    quota: null,
    subscription: null,
    plans: [],
    models: [
      {
        model_id: "ai-model-flash-1",
        tier: "flash",
        display_name: "tblinc Flash",
        description: "tblinc AI — ultra-low-latency chat, drafts & quick previews",
        primary_backend: "numpy",
        credit_cost: { chat: 1, code: 2, images: 4, video: 8 },
        hidden_dim: 128,
        num_layers: 2,
      },
      {
        model_id: "ai-model-pro-1",
        tier: "pro",
        display_name: "tblinc Pro",
        description: "tblinc AI — balanced reasoning & high-detail media",
        primary_backend: "tensorflow",
        credit_cost: { chat: 3, code: 5, images: 10, video: 20 },
        hidden_dim: 256,
        num_layers: 4,
      },
      {
        model_id: "ai-model-advance-1",
        tier: "advance",
        display_name: "tblinc Advance",
        description: "tblinc AI — complex synthesis & studio media",
        primary_backend: "hybrid",
        credit_cost: { chat: 6, code: 10, images: 18, video: 36 },
        hidden_dim: 512,
        num_layers: 6,
      },
    ],
    transactions: [],
    invoices: [],
    verification: null,
    adminOverview: null,
    adminBusy: false,
    agents: [],
    agentRuns: [],
    health: null,
    fastapiBaseUrl: window.__FASTAPI_BASE_URL__ || "http://127.0.0.1:8001",

    activeSection: initialRoute.section,
    adminTab: initialRoute.adminTab || "mfs",
    settingsTab: initialRoute.settingsTab,
    theme: localStorage.getItem("theme") === "light" ? "light" : "dark",
    sidebarOpen: false,
    sidebarCollapsed: localStorage.getItem("sidebarCollapsed") === "true",
    modelDropdownOpen: false,
    showUserMenu: false,
    showSidebarUserMenu: false,
    modelViewMode: "card",
    activeTier: initialTier,
    activeTask: initialRoute.task,
    activeBackend: "numpy",
    prompt: "",
    studioAttachment: null,
    voiceMode: false,
    liveMode: false,
    language: "python",
    videoDurationSeconds: 600,
    systemPrompt: "",
    loading: false,
    error: "",
    notice: "",
    outputs: [],
    conversations: [],
    activeConversation: null,
    trainingStatus: null,
    trainingResult: null,
    trainingSamples: [],
    trainingHistory: [],
    trainingCheckpoints: [],
    trainingEvalResult: null,
    trainingConfig: {
      epochs: 8,
      learningRate: 0.012,
      includeBuiltin: true,
      includeConversations: true,
    },
    trainingBusy: false,

    showAuthModal: false,
    authMode: initialRoute.authMode || "login",
    postAuthPath: initialPostAuthPath,
    authError: "",
    authBusy: false,
    showPassword: false,
    showTopupModal: false,
    checkoutMode: "credits",
    checkoutMethod: "bkash",
    checkoutTnxid: "",
    checkoutPlanSlug: "",
    checkoutError: "",
    checkoutBusy: false,
    checkoutReceipt: null,
    showNotifications: false,
    notifications: [],
  });
};

window.AIModelBilling = (() => {
  const USD_PER_CREDIT = 0.01;
  const BDT_PER_USD = 120;

  function usdToBdt(amountUsd) {
    const val = Number(amountUsd || 0);
    return Number.isFinite(val) && val > 0 ? Math.round(val * BDT_PER_USD * 100) / 100 : 0;
  }

  function formatBdt(amountBdt) {
    const val = Number(amountBdt || 0);
    return "৳" + (Number.isFinite(val) ? val : 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatUsd(amountUsd) {
    const val = Number(amountUsd || 0);
    return "$" + (Number.isFinite(val) ? val : 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function creditsToUsdNumber(credits) {
    const n = Number(credits || 0);
    if (!Number.isFinite(n)) return 0;
    return Math.round(n * USD_PER_CREDIT * 100) / 100;
  }

  function formatCreditsBdtUsd(credits, options = {}) {
    const raw = Number(credits || 0);
    const safe = Number.isFinite(raw) ? raw : 0;
    const sign = options.signed ? (safe > 0 ? "+" : safe < 0 ? "-" : "") : safe < 0 ? "-" : "";
    const absVal = Math.abs(safe);
    const usd = creditsToUsdNumber(absVal);
    const bdt = usdToBdt(usd.toFixed(2));
    if (options.compact) {
      return `${sign}${formatBdt(bdt)} (${formatUsd(usd)})`;
    }
    return `${sign}${formatBdt(bdt)} BDT · ${formatUsd(usd)} USD`;
  }

  function formatRangeBdtUsd(minCredits, maxCredits) {
    const minUsd = creditsToUsdNumber(minCredits);
    const maxUsd = creditsToUsdNumber(maxCredits);
    const minBdt = usdToBdt(minUsd.toFixed(2));
    const maxBdt = usdToBdt(maxUsd.toFixed(2));
    return `${formatBdt(minBdt)}–${formatBdt(maxBdt)} BDT (${formatUsd(minUsd)}–${formatUsd(maxUsd)})`;
  }

  return {
    USD_PER_CREDIT,
    BDT_PER_USD,
    usdToBdt,
    formatBdt,
    formatUsd,
    creditsToUsdNumber,
    formatCreditsBdtUsd,
    formatRangeBdtUsd,
  };
})();

