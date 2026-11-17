import { useState } from "react";
import { Check, Copy, KeyRound, Plus, Power, ShieldCheck, Trash2 } from "lucide-react";
import { SecretKeyItem } from "../types/ai";

interface ApiKeysViewProps {
  secretKeys: SecretKeyItem[];
  authenticated: boolean;
  onCreateKey: (name: string) => Promise<SecretKeyItem | null>;
  onToggleKey: (id: number, nextActive: boolean) => Promise<void>;
  onDeleteKey: (id: number) => Promise<void>;
  onOpenAuth: () => void;
}

export function ApiKeysView({
  secretKeys,
  authenticated,
  onCreateKey,
  onToggleKey,
  onDeleteKey,
  onOpenAuth,
}: ApiKeysViewProps) {
  const [keyLabel, setKeyLabel] = useState("Default API Key");
  const [creating, setCreating] = useState(false);
  const [revealedKey, setRevealedKey] = useState("");
  const [copied, setCopied] = useState(false);

  if (!authenticated) {
    return (
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-6 text-center space-y-2.5">
        <KeyRound className="w-8 h-8 text-cyan-600 dark:text-cyan-400 mx-auto" />
        <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
          Sign In to Manage API Keys
        </h3>
        <button
          type="button"
          onClick={onOpenAuth}
          className="px-4 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold"
        >
          Sign In
        </button>
      </div>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (creating) return;
    setCreating(true);
    try {
      const created = await onCreateKey(keyLabel.trim() || "API Key");
      if (created?.secret_key) {
        setRevealedKey(created.secret_key);
        setCopied(false);
      }
      setKeyLabel("Workspace API Key");
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!revealedKey) return;
    await navigator.clipboard.writeText(revealedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="space-y-4">
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>API Keys</span>
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              Create, pause, or revoke secret API keys for calling tblinc models programmatically.
            </p>
          </div>

          <form onSubmit={handleCreate} className="flex items-center gap-2">
            <input
              type="text"
              value={keyLabel}
              onChange={(e) => setKeyLabel(e.target.value)}
              placeholder="Key label..."
              className="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 w-44"
            />
            <button
              type="submit"
              disabled={creating}
              className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{creating ? "Creating..." : "Create API Key"}</span>
            </button>
          </form>
        </div>

        {revealedKey && (
          <div className="rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/35 p-3.5 space-y-2">
            <div className="flex items-center justify-between gap-2 text-xs font-semibold text-emerald-800 dark:text-emerald-300">
              <span>New API Key Created (copy now — shown once)</span>
              <button
                type="button"
                onClick={() => void handleCopy()}
                className="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] flex items-center gap-1"
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? "Copied" : "Copy Key"}</span>
              </button>
            </div>
            <div className="font-mono text-xs break-all text-slate-900 dark:text-white bg-white/90 dark:bg-slate-950 px-3 py-2 rounded-lg border border-emerald-200 dark:border-emerald-500/20">
              {revealedKey}
            </div>
          </div>
        )}

        <div className="space-y-2">
          {secretKeys.map((k) => (
            <div
              key={k.id}
              className="rounded-xl bg-slate-50 dark:bg-slate-950/75 border border-slate-200 dark:border-slate-800 px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs"
            >
              <div className="min-w-0 space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900 dark:text-white truncate">{k.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full font-mono text-[10px] ${
                      k.is_active
                        ? "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                        : "bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    {k.is_active ? "Active" : "Paused"}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  {k.key_prefix}•••••••• · Created {k.created_at.slice(0, 10)}
                  {k.last_used_at ? ` · Last used ${k.last_used_at.slice(0, 10)}` : ""}
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => void onToggleKey(k.id, !k.is_active)}
                  className="px-2.5 py-1 rounded-lg bg-slate-200/80 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-[11px] font-semibold flex items-center gap-1"
                  title={k.is_active ? "Pause key" : "Activate key"}
                >
                  <Power className="w-3 h-3" />
                  <span>{k.is_active ? "Pause" : "Enable"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => void onDeleteKey(k.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10"
                  title="Revoke & delete API key"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
          {!secretKeys.length && (
            <p className="text-xs text-slate-500 py-4 text-center">No API keys created yet.</p>
          )}
        </div>

        <div className="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3 space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-700 dark:text-slate-200">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
            <span>Authentication Header</span>
          </div>
          <code className="block text-[11px] font-mono text-slate-600 dark:text-slate-400 break-all">
            X-API-Key: sk_tblinc_...  or  Authorization: Bearer sk_tblinc_...
          </code>
        </div>
      </div>
    </div>
  );
}

