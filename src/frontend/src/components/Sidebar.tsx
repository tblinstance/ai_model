import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import {
  BarChart3,
  ChevronDown,
  Code2,
  Coins,
  Cpu,
  Film,
  Gauge,
  Image as ImageIcon,
  LayoutDashboard,
  LayoutGrid,
  LogOut,
  MessageSquare,
  MoreVertical,
  Settings,
  Sparkles,
  User,
  X,
  Zap,
} from "lucide-react";
import { ModelSummary, ModelTier, NavSection, QuotaStatus, TaskType, UserProfile } from "../types/ai";
import { formatCreditsBdtUsd } from "../services/payment";
import { AuthMode } from "./AuthModal";
import { UserAvatar } from "./UserAvatar";

interface SidebarProps {
  activeSection: NavSection;
  activeTask: TaskType;
  onSelectSection: (section: NavSection) => void;
  onSelectTaskLink: (task: TaskType) => void;
  activeTier: ModelTier;
  onSelectTier: (tier: ModelTier) => void;
  models: ModelSummary[];
  quota: QuotaStatus | null;
  authenticated: boolean;
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onExpandSidebar: () => void;
  onOpenAuth: (mode?: AuthMode) => void;
  user?: UserProfile | null;
  onOpenProfile?: () => void;
  onOpenBilling?: () => void;
  onOpenSettings?: () => void;
  onLogout?: () => void;
}

export const NAV_ITEMS: Array<{ id: NavSection; label: string; icon: typeof LayoutDashboard; colorClass?: string }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard, colorClass: "text-indigo-600 dark:text-indigo-400" },
  { id: "analytics", label: "Dashboard", icon: BarChart3, colorClass: "text-sky-600 dark:text-sky-400" },
  { id: "settings", label: "Settings", icon: Settings, colorClass: "text-cyan-600 dark:text-cyan-400" },
];

export const TASK_NAV_ITEMS: Array<{ id: TaskType; label: string; icon: typeof MessageSquare; colorClass?: string }> = [
  { id: "chat", label: "tblinc Chat", icon: MessageSquare, colorClass: "text-cyan-600 dark:text-cyan-400" },
  { id: "images", label: "tblinc Images", icon: ImageIcon, colorClass: "text-purple-600 dark:text-purple-400" },
  { id: "video", label: "tblinc Video", icon: Film, colorClass: "text-rose-600 dark:text-rose-400" },
  { id: "code", label: "tblinc Code", icon: Code2, colorClass: "text-emerald-600 dark:text-emerald-400" },
];

const SWITCHER_MODELS: Array<{
  tier: ModelTier;
  label: string;
  icon: typeof Zap;
  colorClass: string;
}> = [
    { tier: "flash", label: "tblinc Flash", icon: Zap, colorClass: "text-cyan-600 dark:text-cyan-400" },
    { tier: "pro", label: "tblinc Pro", icon: Cpu, colorClass: "text-indigo-600 dark:text-indigo-400" },
    { tier: "advance", label: "tblinc Advance", icon: Sparkles, colorClass: "text-purple-600 dark:text-purple-400" },
  ];

export function Sidebar({
  activeSection,
  activeTask,
  onSelectSection,
  onSelectTaskLink,
  activeTier,
  onSelectTier,
  models,
  quota,
  authenticated,
  open,
  collapsed,
  onClose,
  onExpandSidebar,
  onOpenAuth,
  user,
  onOpenProfile,
  onOpenBilling,
  onOpenSettings,
  onLogout,
}: SidebarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const switcherRef = useRef<HTMLDivElement | null>(null);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (switcherRef.current && !switcherRef.current.contains(target)) {
        setDropdownOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("click", handleDocClick);
    return () => document.removeEventListener("click", handleDocClick);
  }, []);

  const switcherItems = SWITCHER_MODELS.map((item) => {
    const live = models.find((m) => m.tier === item.tier);
    return {
      ...item,
      label: live?.display_name || item.label,
    };
  });

  const activeItem = switcherItems.find((item) => item.tier === activeTier) || switcherItems[0];

  const pct = quota
    ? Math.min(100, Math.round((quota.remaining_credits / Math.max(1, quota.total_credits)) * 100))
    : 0;

  return (
    <>
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-xs z-40 lg:hidden"
          aria-hidden="true"
        />
      )}

      <aside
        className={`${open ? "flex" : "hidden lg:flex"
          } fixed inset-y-0 left-0 z-50 lg:static lg:z-auto w-64 ${collapsed ? "lg:w-[4.5rem]" : "lg:w-64"
          } h-full shrink-0 bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border-r border-slate-200 dark:border-slate-800/80 flex-col justify-between overflow-hidden transition-all duration-300`}
      >
        <div className="flex-1 flex flex-col min-h-0">
          {/* Sidebar Brand Header (matches /home/v1/deployment h-16 logo slot) */}
          <div
            className={`h-16 border-b border-slate-200 dark:border-slate-800/80 flex items-center shrink-0 ${collapsed ? "lg:justify-center lg:px-0 px-4 justify-between" : "px-4 justify-between"
              }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <img
                src="/tblinc-ai-icon.svg"
                alt="tblinc AI"
                className="w-9 h-9 rounded-xl shadow-lg shadow-indigo-500/25 shrink-0"
              />
              {!collapsed && (
                <div className="truncate">
                  <div className="font-display font-bold text-slate-900 dark:text-white leading-tight text-sm">tblinc AI</div>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800"
              aria-label="Close navigation"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* System Switcher (matches /home/v1/deployment dashboard switcher) */}
          <div ref={switcherRef} className="px-3 py-3 border-b border-slate-200 dark:border-slate-800/80 shrink-0">
            <button
              type="button"
              onClick={() => {
                if (collapsed) {
                  onExpandSidebar();
                  setDropdownOpen(true);
                } else {
                  setDropdownOpen((prev) => !prev);
                }
              }}
              aria-expanded={dropdownOpen && !collapsed}
              title={activeItem.label}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 font-semibold text-xs hover:bg-indigo-100 dark:hover:bg-indigo-500/25 transition-colors ${collapsed ? "lg:justify-center lg:px-0" : ""
                }`}
            >
              <LayoutGrid className="w-4 h-4 shrink-0" />
              {!collapsed && (
                <>
                  <span className="flex-1 text-left truncate">{activeItem.label}</span>
                  <ChevronDown
                    className={`w-4 h-4 shrink-0 transition-transform ${dropdownOpen ? "rotate-180" : ""
                      }`}
                  />
                </>
              )}
            </button>

            {dropdownOpen && !collapsed && (
              <div className="mt-2 flex flex-col gap-0.5">
                {switcherItems.map((item) => {
                  const Icon = item.icon;
                  const selected = item.tier === activeTier;
                  return (
                    <button
                      key={item.tier}
                      type="button"
                      onClick={() => {
                        onSelectTier(item.tier);
                        setDropdownOpen(false);
                      }}
                      className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${selected
                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold"
                        : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/70 hover:text-slate-900 dark:hover:text-white"
                        }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${item.colorClass}`} />
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-1">
            {!collapsed && (
              <div className="px-3 pt-1 pb-1.5 text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-500">
                tblinc AI Models
              </div>
            )}

            {TASK_NAV_ITEMS.map((taskItem) => {
              const Icon = taskItem.icon;
              const active = activeSection === "studio" && activeTask === taskItem.id;
              return (
                <motion.button
                  key={taskItem.id}
                  whileHover={{ x: collapsed ? 0 : 2 }}
                  whileTap={{ scale: 0.98 }}
                  title={taskItem.label}
                  onClick={() => {
                    onSelectTaskLink(taskItem.id);
                    onClose();
                  }}
                  className={`w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium transition border ${collapsed ? "lg:justify-center lg:px-0" : ""
                    } ${active
                      ? "bg-cyan-50 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-200 dark:border-cyan-500/35 shadow-sm"
                      : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60 border-transparent"
                    }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${taskItem.colorClass || "text-cyan-600 dark:text-cyan-400"}`} />
                  {!collapsed && <span className="truncate">{taskItem.label}</span>}
                </motion.button>
              );
            })}

            <div className="pt-3 mt-2 border-t border-slate-200/80 dark:border-slate-800/80 space-y-1">
              {!collapsed && (
                <div className="px-3 pb-1 text-[11px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-500">
                  Settings
                </div>
              )}

              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = activeSection === item.id;
                return (
                  <motion.button
                    key={item.id}
                    whileHover={{ x: collapsed ? 0 : 2 }}
                    whileTap={{ scale: 0.98 }}
                    title={item.label}
                    onClick={() => {
                      onSelectSection(item.id);
                      onClose();
                    }}
                    className={`w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-medium transition border ${collapsed ? "lg:justify-center lg:px-0" : ""
                      } ${active
                        ? "bg-indigo-50 dark:bg-indigo-600/25 text-indigo-700 dark:text-white border-indigo-200 dark:border-indigo-500/40 shadow-sm"
                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60 border-transparent"
                      }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${item.colorClass || "text-indigo-600 dark:text-cyan-400"}`} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </motion.button>
                );
              })}
            </div>
          </nav>
        </div>

        <div className="p-3 border-t border-slate-200 dark:border-slate-800/80 shrink-0">
          {collapsed ? (
            <button
              type="button"
              onClick={onExpandSidebar}
              title={`Quota (${activeTier.toUpperCase()})`}
              className="w-full py-2 rounded-xl bg-slate-100 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 flex items-center justify-center text-cyan-600 dark:text-cyan-400 hover:bg-slate-200 dark:hover:bg-slate-800/80 transition"
            >
              <Gauge className="w-4 h-4" />
            </button>
          ) : (
            <div className="rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 p-3.5 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-600 dark:text-slate-400 flex items-center gap-1.5">
                  <Gauge className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                  Quota
                </span>
                <span className="font-mono uppercase text-[11px] px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-cyan-700 dark:text-cyan-300">
                  {activeTier}
                </span>
              </div>

              {authenticated && quota ? (
                <>
                  <div className="flex justify-between items-baseline gap-2 text-[11px] font-mono">
                    <span className="text-slate-600 dark:text-slate-400">Balance</span>
                    <span className="text-slate-900 dark:text-white font-medium truncate">
                      {formatCreditsBdtUsd(quota.remaining_credits, { compact: true })}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-500">
                    Daily calls: {quota.daily_requests}/{quota.max_daily_requests}
                  </div>
                </>
              ) : (
                <div className="space-y-2.5">
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                    Preview mode active. Login or sign up to sync quota, billing, and history.
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        onOpenAuth("login");
                      }}
                      className="py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-semibold"
                    >
                      Login
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        onOpenAuth("register");
                      }}
                      className="py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
                    >
                      Sign Up
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* User Avatar + More Popover */}
          {authenticated && user && (
            <div ref={userMenuRef} className="relative mt-2.5 pt-2 border-t border-slate-200/80 dark:border-slate-800/80">
              <div
                className={`w-full flex items-center gap-2 rounded-xl p-1.5 transition ${
                  userMenuOpen
                    ? "bg-slate-100 dark:bg-slate-800"
                    : "hover:bg-slate-100 dark:hover:bg-slate-800/70"
                } ${collapsed ? "justify-center" : "justify-between"}`}
              >
                <button
                  type="button"
                  onClick={() => onOpenProfile?.()}
                  title={`Open My Profile (@${user.username})`}
                  className="flex items-center gap-2.5 min-w-0 group cursor-pointer text-left"
                >
                  <UserAvatar
                    avatar={user.avatar}
                    name={user.display_name || user.username}
                    sizeClass="w-8 h-8"
                    textSizeClass="text-xs"
                    className="ring-1 ring-cyan-500/30 group-hover:ring-cyan-500"
                  />
                  {!collapsed && (
                    <div className="text-left min-w-0 pr-1">
                      <div className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate group-hover:text-indigo-600 dark:group-hover:text-cyan-400 transition">
                        {user.display_name || user.username}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">
                        @{user.username}
                      </div>
                    </div>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setUserMenuOpen((prev) => !prev)}
                  title="More account options"
                  aria-expanded={userMenuOpen}
                  className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <MoreVertical className="w-4 h-4 shrink-0" />
                </button>
              </div>

              {userMenuOpen && (
                <div
                  className={`absolute ${
                    collapsed ? "left-full ml-3 bottom-0" : "bottom-full left-0 mb-2"
                  } w-56 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-2 space-y-1 z-50`}
                >
                  <div
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenProfile?.();
                    }}
                    className="px-3 py-2 border-b border-slate-200/80 dark:border-slate-800/80 mb-1 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60 rounded-xl transition"
                    title="View My Profile"
                  >
                    <div className="flex items-center gap-2">
                      <UserAvatar
                        avatar={user.avatar}
                        name={user.display_name || user.username}
                        sizeClass="w-7 h-7"
                        textSizeClass="text-[10px]"
                        className="ring-1 ring-cyan-500/40"
                      />
                      <div className="min-w-0">
                        <div className="font-semibold text-xs text-slate-900 dark:text-white truncate">
                          {user.display_name || user.username}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">
                          @{user.username} · {user.plan_name || "Free"}
                        </div>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenProfile?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <User className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                    <span>My Profile</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenBilling?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Coins className="w-4 h-4 text-amber-500" />
                    <span>Billing & Quota</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenSettings?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Settings className="w-4 h-4 text-slate-500" />
                    <span>Settings</span>
                  </button>

                  <div className="border-t border-slate-200/80 dark:border-slate-800/80 my-1" />

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onLogout?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
