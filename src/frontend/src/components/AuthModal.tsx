import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { AlertCircle, Eye, EyeOff, LogIn, UserPlus, X } from "lucide-react";

export type AuthMode = "login" | "register";

interface AuthModalProps {
  open: boolean;
  mode: AuthMode;
  error: string;
  onModeChange: (mode: AuthMode) => void;
  onClearError: () => void;
  onClose: () => void;
  onSubmit: (mode: AuthMode, username: string, email: string, password: string) => Promise<void>;
}

export function AuthModal({
  open,
  mode,
  error,
  onModeChange,
  onClearError,
  onClose,
  onSubmit,
}: AuthModalProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setLocalError("");
      setShowPassword(false);
    }
  }, [open, mode]);

  if (!open) return null;

  const activeError = localError || error;

  const switchMode = (next: AuthMode) => {
    setLocalError("");
    onClearError();
    onModeChange(next);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError("");
    onClearError();

    const trimmedUser = username.trim();
    if (!trimmedUser) {
      setLocalError("Username is required.");
      return;
    }
    if (mode === "register") {
      if (password.length < 8) {
        setLocalError("Password must be at least 8 characters.");
        return;
      }
      if (password !== confirmPassword) {
        setLocalError("Passwords do not match.");
        return;
      }
    }

    setBusy(true);
    try {
      await onSubmit(mode, trimmedUser, email.trim(), password);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/55 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-display text-lg font-bold text-slate-900 dark:text-white">
              {mode === "login" ? "Welcome Back" : "Create tblinc Account"}
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {mode === "login"
                ? "Sign in with your Djoser JWT credentials"
                : "Register to unlock quota, agents, and billing"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close authentication modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <button
            type="button"
            onClick={() => switchMode("login")}
            className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
              mode === "login"
                ? "bg-indigo-600 text-white shadow"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Login</span>
          </button>
          <button
            type="button"
            onClick={() => switchMode("register")}
            className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
              mode === "register"
                ? "bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Sign Up</span>
          </button>
        </div>

        {activeError && (
          <div className="rounded-xl bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/40 px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-200 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
            <span className="break-words">{activeError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              autoComplete="username"
              required
              className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-500 focus:outline-none"
            />
          </div>

          {mode === "register" && (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
                className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Password</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "Minimum 8 characters" : "Enter password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 pl-3.5 pr-10 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {mode === "register" && (
            <div className="space-y-1">
              <label className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Confirm Password</label>
              <input
                type={showPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                autoComplete="new-password"
                required
                className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>
          )}

          <button
            disabled={busy}
            type="submit"
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white text-sm font-semibold disabled:opacity-50"
          >
            {busy ? "Authenticating..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
