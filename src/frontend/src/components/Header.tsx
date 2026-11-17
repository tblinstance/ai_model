import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Coins,
  Key,
  LogIn,
  LogOut,
  Menu,
  Moon,
  MoreVertical,
  Settings2,
  ShoppingBag,
  Sun,
  User,
  UserPlus,
} from "lucide-react";
import { EngineHealthResponse, ModelTier, NotificationItem, QuotaStatus, UserProfile } from "../types/ai";
import { formatCreditsBdtUsd } from "../services/payment";
import { AuthMode } from "./AuthModal";
import { UserAvatar } from "./UserAvatar";

interface HeaderProps {
  sectionTitle: string;
  activeTier: ModelTier;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  health: EngineHealthResponse | null;
  user: UserProfile | null;
  quota: QuotaStatus | null;
  notifications: NotificationItem[];
  onMarkAllRead?: () => void;
  onClearNotifications?: () => void;
  authenticated: boolean;
  onToggleSidebar: () => void;
  onOpenAuth: (mode?: AuthMode) => void;
  onOpenProfile?: () => void;
  onOpenBilling?: () => void;
  onOpenCheckout?: () => void;
  onOpenKeys?: () => void;
  onOpenSettings?: () => void;
  onRefreshHealth?: () => void;
  onLogout: () => void;
}

export function Header({
  sectionTitle,
  activeTier,
  theme,
  onToggleTheme,
  health,
  user,
  quota,
  notifications,
  onMarkAllRead,
  onClearNotifications,
  authenticated,
  onToggleSidebar,
  onOpenAuth,
  onOpenProfile,
  onOpenBilling,
  onOpenCheckout,
  onOpenKeys,
  onOpenSettings,
  onRefreshHealth,
  onLogout,
}: HeaderProps) {
  const [notifyOpen, setNotifyOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const notifyRef = useRef<HTMLDivElement | null>(null);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleDocClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (notifyRef.current && !notifyRef.current.contains(target)) {
        setNotifyOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("click", handleDocClick);
    return () => document.removeEventListener("click", handleDocClick);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;
  const fastapiStatus = health?.fastapi?.status;
  const fastapiOnline = fastapiStatus === "ok";
  const checkingHealth = authenticated && health === null;
  const balanceLabel = quota ? formatCreditsBdtUsd(quota.remaining_credits) : "";

  return (
    <header className="h-16 bg-white/85 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800/80 px-4 sm:px-6 flex items-center justify-between gap-4 shrink-0 z-10 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/70 transition-colors shrink-0"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="font-display font-semibold text-base sm:text-lg text-slate-900 dark:text-white truncate">
          {sectionTitle}
        </h1>
        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/30 text-[11px] font-mono text-indigo-700 dark:text-indigo-300 uppercase shrink-0">
          tblinc {activeTier}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleTheme}
          className="p-2 rounded-xl bg-slate-100 dark:bg-slate-950/90 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-cyan-300 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors"
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          title={theme === "dark" ? "Light Mode" : "Dark Mode"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {authenticated && (
          <button
            type="button"
            onClick={onRefreshHealth}
            title="Refresh AI status"
            className={`hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border transition-colors ${
              fastapiOnline
                ? "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                : checkingHealth
                  ? "border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-300"
                  : "border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                fastapiOnline
                  ? "bg-emerald-500 dark:bg-emerald-400"
                  : checkingHealth
                    ? "bg-slate-400 animate-pulse"
                    : "bg-amber-500 dark:bg-amber-400"
              }`}
            />
            <span>{checkingHealth ? "AI Checking" : fastapiOnline ? "AI Online" : "AI Offline"}</span>
          </button>
        )}

        {authenticated && user ? (
          <div className="flex items-center gap-2">
            {quota && (
              <button
                type="button"
                onClick={onOpenBilling}
                title={`Balance: ${balanceLabel} (${quota.remaining_credits.toLocaleString()} credits)`}
                className="inline-flex items-center gap-1 text-[11px] font-mono font-medium px-2 py-1 rounded-lg bg-cyan-50 dark:bg-cyan-500/10 border border-cyan-200 dark:border-cyan-500/30 text-cyan-800 dark:text-cyan-300 hover:bg-cyan-100 dark:hover:bg-cyan-500/20 transition-colors"
              >
                <Coins className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                <span>{balanceLabel}</span>
              </button>
            )}
            {onOpenCheckout && (
              <button
                type="button"
                onClick={onOpenCheckout}
                title="Deposit Credits or Upgrade Plan"
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white shadow-sm shadow-indigo-600/25 transition-opacity"
              >
                <ShoppingBag className="w-3.5 h-3.5" />
                <span>Deposit</span>
              </button>
            )}
            <div ref={notifyRef} className="relative">
              <button
                type="button"
                onClick={() => setNotifyOpen((prev) => !prev)}
                title="Notifications"
                aria-label="Notifications"
                className="relative p-2 rounded-xl bg-slate-100 dark:bg-slate-950/90 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-cyan-300 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-cyan-500 text-white text-[10px] font-mono font-bold flex items-center justify-center">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {notifyOpen && (
                <div className="absolute right-0 mt-2 w-80 max-w-[90vw] rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-2xl p-3 space-y-2 z-50">
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                    <span className="font-display font-semibold text-xs text-slate-900 dark:text-white">
                      Notifications ({notifications.length})
                    </span>
                    <div className="flex items-center gap-2 text-[11px]">
                      {unreadCount > 0 && onMarkAllRead && (
                        <button
                          type="button"
                          onClick={onMarkAllRead}
                          className="text-indigo-600 dark:text-cyan-400 hover:underline font-medium"
                        >
                          Mark read
                        </button>
                      )}
                      {notifications.length > 0 && onClearNotifications && (
                        <button
                          type="button"
                          onClick={() => {
                            onClearNotifications();
                            setNotifyOpen(false);
                          }}
                          className="text-slate-500 hover:text-rose-500"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-1.5 pr-0.5">
                    {notifications.map((item) => (
                      <div
                        key={item.id}
                        className={`rounded-xl px-2.5 py-2 text-xs border transition ${
                          item.read
                            ? "bg-slate-50/70 dark:bg-slate-950/40 border-slate-200/70 dark:border-slate-800/70"
                            : "bg-cyan-50/70 dark:bg-cyan-500/10 border-cyan-200 dark:border-cyan-500/30"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-slate-900 dark:text-white truncate">{item.title}</span>
                          <span className="text-[10px] font-mono text-slate-400 shrink-0">{item.time}</span>
                        </div>
                        <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 line-clamp-2">
                          {item.message}
                        </p>
                      </div>
                    ))}
                    {!notifications.length && (
                      <p className="text-xs text-slate-500 text-center py-4">No notifications yet.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
            {/* User Avatar + More Options Menu */}
            <div ref={userMenuRef} className="relative">
              <div className="flex items-center rounded-full bg-slate-100 dark:bg-slate-950/90 border border-slate-200 dark:border-slate-800 hover:border-cyan-500/50 hover:bg-slate-200/70 dark:hover:bg-slate-800 transition p-1 pl-1.5 pr-1.5 gap-1.5 shadow-xs">
                <button
                  type="button"
                  onClick={() => onOpenProfile?.()}
                  title={`Open My Profile (@${user.username})`}
                  className="flex items-center gap-2 group cursor-pointer text-left"
                >
                  <UserAvatar
                    avatar={user.avatar}
                    name={user.display_name || user.username}
                    sizeClass="w-7 h-7"
                    textSizeClass="text-xs"
                    className="ring-1 ring-cyan-500/30 group-hover:ring-cyan-500"
                  />
                  <div className="hidden sm:flex flex-col text-left leading-none min-w-0 pr-1">
                    <span className="text-xs font-semibold text-slate-800 dark:text-slate-100 truncate max-w-[110px] group-hover:text-indigo-600 dark:group-hover:text-cyan-400 transition">
                      {user.display_name || `@${user.username}`}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                      {user.is_superuser ? "Superuser" : user.is_staff ? "Staff" : "Member"}
                    </span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => setUserMenuOpen((prev) => !prev)}
                  title="More account options"
                  aria-expanded={userMenuOpen}
                  className="p-1 rounded-full hover:bg-slate-300/60 dark:hover:bg-slate-700/80 transition text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <MoreVertical className="w-3.5 h-3.5 shrink-0" />
                </button>
              </div>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-2 space-y-1 z-50">
                  <div
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenProfile?.();
                    }}
                    className="px-3 py-2.5 border-b border-slate-200/80 dark:border-slate-800/80 mb-1 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60 rounded-xl transition"
                    title="View My Profile"
                  >
                    <div className="flex items-center gap-2.5">
                      <UserAvatar
                        avatar={user.avatar}
                        name={user.display_name || user.username}
                        sizeClass="w-9 h-9"
                        textSizeClass="text-sm"
                        className="ring-2 ring-indigo-500/40"
                      />
                      <div className="min-w-0">
                        <div className="font-semibold text-xs text-slate-900 dark:text-white truncate">
                          {user.display_name || user.username}
                        </div>
                        <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400 truncate">
                          @{user.username}
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
                      onOpenKeys?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Key className="w-4 h-4 text-indigo-500" />
                    <span>API Keys</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onOpenSettings?.();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                  >
                    <Settings2 className="w-4 h-4 text-slate-500" />
                    <span>Settings</span>
                  </button>

                  <div className="border-t border-slate-200/80 dark:border-slate-800/80 my-1" />

                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false);
                      onLogout();
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenAuth("login")}
              className="px-3.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Login</span>
            </button>
            <button
              type="button"
              onClick={() => onOpenAuth("register")}
              className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/25"
            >
              <UserPlus className="w-3.5 h-3.5" />
              <span>Sign Up</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

