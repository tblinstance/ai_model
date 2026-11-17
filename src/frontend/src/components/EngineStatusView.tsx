import { Check, Cpu, Sparkles, Zap } from "lucide-react";
import { ModelSummary, ModelTier } from "../types/ai";

interface EngineStatusViewProps {
  models: ModelSummary[];
  activeTier: ModelTier;
  onSelectTier: (tier: ModelTier) => void;
}

const TIER_ICONS: Record<ModelTier, typeof Zap> = {
  flash: Zap,
  pro: Cpu,
  advance: Sparkles,
};

/**
 * User-facing model tier catalog allowing activation across Flash, Pro, and Advance.
 */
export function EngineStatusView({
  models,
  activeTier,
  onSelectTier,
}: EngineStatusViewProps) {
  return (
    <div className="bg-white/90 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
      <div>
        <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          <span>tblinc AI Model Tiers</span>
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
          Choose the speed and reasoning depth used across AI Chat, Images, Videos, and Code.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {models.map((m) => {
          const isActive = m.tier === activeTier;
          const Icon = TIER_ICONS[m.tier] || Cpu;
          return (
            <div
              key={m.model_id}
              className={`rounded-xl bg-slate-50 dark:bg-slate-950/80 border p-3.5 space-y-2.5 flex flex-col justify-between ${
                isActive
                  ? "border-cyan-500/70 dark:border-cyan-500/60 shadow-sm shadow-cyan-500/10"
                  : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                    <Icon className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
                    <span>{m.display_name}</span>
                  </div>
                  {isActive && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      Active
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">{m.description}</p>
                <div className="text-[11px] font-mono text-slate-700 dark:text-slate-300 pt-1 space-y-0.5">
                  <div>Context Limit: {m.max_tokens.toLocaleString()} tokens</div>
                  <div>
                    Credits: Chat {m.credit_cost?.chat ?? 1} · Image {m.credit_cost?.images ?? 3} · Video{" "}
                    {m.credit_cost?.video ?? 6} · Code {m.credit_cost?.code ?? 2} · Audio {m.credit_cost?.audio ?? 2}
                  </div>
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
                {isActive ? "Active Across Workspace" : `Activate ${m.display_name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
