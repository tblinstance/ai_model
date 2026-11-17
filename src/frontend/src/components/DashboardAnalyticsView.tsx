import { Activity, BarChart3, Clock, Coins, MessageSquare, Sparkles, TrendingUp } from "lucide-react";
import { formatCreditsBdtUsd } from "../services/payment";
import {
  ConversationSummary,
  DashboardAnalytics,
  ModelTier,
  TaskType,
} from "../types/ai";

interface DashboardAnalyticsViewProps {
  analytics: DashboardAnalytics | null;
  conversations: ConversationSummary[];
  activeTier: ModelTier;
  onQuickTask: (task: TaskType) => void;
  onOpenConversation: (id: number) => void;
}

const TIER_COLORS: Record<string, string> = {
  flash: "from-cyan-500 to-sky-500",
  pro: "from-indigo-500 to-blue-600",
  advance: "from-purple-500 to-fuchsia-600",
};

const TASK_COLORS: Record<string, string> = {
  chat: "from-indigo-500 to-cyan-500",
  images: "from-emerald-500 to-teal-500",
  video: "from-amber-500 to-orange-500",
  code: "from-purple-500 to-indigo-500",
};

export function DashboardAnalyticsView({
  analytics,
  conversations,
  activeTier,
  onQuickTask,
  onOpenConversation,
}: DashboardAnalyticsViewProps) {
  const summary = analytics?.summary;
  const daily = analytics?.daily_activity || [];
  const byTier = analytics?.by_tier || [];
  const byTask = analytics?.by_task || [];
  const recentLogs = analytics?.recent_logs || [];

  const maxDailyReqs = Math.max(1, ...daily.map((d) => d.requests));
  const totalRequests = Math.max(1, summary?.total_requests || 0);
  const creditPct = summary
    ? Math.min(100, Math.round((summary.remaining_credits / Math.max(1, summary.total_credits)) * 100))
    : 0;

  return (
    <div className="space-y-4">
      {/* Top KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-1.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Total Requests</span>
            <Activity className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
          </div>
          <div className="font-display text-2xl font-bold text-slate-900 dark:text-white">
            {summary ? summary.total_requests.toLocaleString() : "0"}
          </div>
          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            Today: {summary?.daily_requests ?? 0} / {summary?.max_daily_requests ?? 250} calls
          </div>
        </div>

        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-1.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Credits Balance</span>
            <Coins className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div className="font-display text-2xl font-bold text-slate-900 dark:text-white">
            {summary ? summary.remaining_credits.toLocaleString() : "0"}
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-300"
              style={{ width: `${creditPct}%` }}
            />
          </div>
          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            Spent: {formatCreditsBdtUsd(summary?.used_credits, { compact: true })} / {formatCreditsBdtUsd(summary?.total_credits, { compact: true })}
          </div>
        </div>

        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-1.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Avg Inference Latency</span>
            <Clock className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="font-display text-2xl font-bold text-slate-900 dark:text-white">
            {summary ? `${summary.avg_latency_ms.toFixed(1)} ms` : "0.0 ms"}
          </div>
          <div className="text-[11px] font-mono text-emerald-700 dark:text-emerald-300">
            Tier {activeTier.toUpperCase()} · Active
          </div>
        </div>

        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-1.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Threads &amp; Agents</span>
            <MessageSquare className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <div className="font-display text-2xl font-bold text-slate-900 dark:text-white">
            {summary?.total_conversations ?? conversations.length}
          </div>
          <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            {summary?.total_messages ?? 0} msgs · {summary?.total_agent_runs ?? 0} agent runs
          </div>
        </div>
      </div>

      {/* Middle Analytics Charts: 7-Day Trend + Tier & Task Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 7-Day Activity Bar Chart */}
        <div className="lg:col-span-7 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
              <span>7-Day Inference &amp; Credit Activity</span>
            </h2>
            <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
              Last 7 days
            </span>
          </div>

          <div className="grid grid-cols-7 gap-2 items-end h-44 pt-4 px-1 border-b border-slate-200 dark:border-slate-800 pb-2">
            {daily.map((day) => {
              const heightPct = day.requests > 0 ? Math.max(12, Math.round((day.requests / maxDailyReqs) * 100)) : 4;
              return (
                <div key={day.date} className="flex flex-col items-center justify-end h-full gap-1.5 group">
                  <div className="text-[10px] font-mono text-slate-600 dark:text-slate-300 opacity-80 group-hover:opacity-100">
                    {day.requests > 0 ? `${day.requests}r` : "0"}
                  </div>
                  <div className="w-full flex items-end justify-center flex-1">
                    <div
                      title={`${day.label}: ${day.requests} requests, ${formatCreditsBdtUsd(day.credits, { compact: true })}, ${day.avg_latency_ms} ms`}
                      style={{ height: `${heightPct}%` }}
                      className={`w-full max-w-[34px] rounded-t-lg transition-all duration-300 ${
                        day.requests > 0
                          ? "bg-gradient-to-t from-indigo-600 via-indigo-500 to-cyan-400 shadow-sm"
                          : "bg-slate-200 dark:bg-slate-800/80"
                      }`}
                    />
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                    {day.label}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <span className="text-[11px] text-slate-500 dark:text-slate-400">Quick Launch Studio:</span>
            <div className="flex flex-wrap gap-1.5">
              {(
                [
                  { id: "chat", label: "AI Chat" },
                  { id: "images", label: "Create Images" },
                  { id: "video", label: "Create Videos" },
                  { id: "code", label: "Create Code" },
                ] as const
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onQuickTask(item.id)}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-700 dark:text-slate-200 text-[11px] font-semibold transition flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Tier & Task Usage Distributions */}
        <div className="lg:col-span-5 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-4 shadow-xs dark:shadow-none">
          <div className="space-y-2.5">
            <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>Usage by Tier &amp; Studio Mode</span>
            </h2>

            <div className="space-y-2">
              {byTier.map((row) => {
                const share = Math.round((row.requests / totalRequests) * 100);
                return (
                  <div key={row.tier} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-mono">
                      <span className="uppercase font-semibold text-slate-800 dark:text-slate-200">tblinc {row.tier}</span>
                      <span className="text-slate-500 dark:text-slate-400">
                        {row.requests} req · {formatCreditsBdtUsd(row.credits, { compact: true })} · {row.avg_latency_ms} ms
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${TIER_COLORS[row.tier] || "from-indigo-500 to-cyan-500"}`}
                        style={{ width: `${row.requests > 0 ? Math.max(4, share) : 0}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-200 dark:border-slate-800">
            {byTask.map((row) => {
              const share = Math.round((row.requests / totalRequests) * 100);
              return (
                <div key={row.task} className="space-y-1">
                  <div className="flex justify-between text-[11px] font-mono">
                    <span className="uppercase font-semibold text-slate-800 dark:text-slate-200">{row.task}</span>
                    <span className="text-slate-500 dark:text-slate-400">
                      {row.requests} req · {formatCreditsBdtUsd(row.credits, { compact: true })}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${TASK_COLORS[row.task] || "from-cyan-500 to-indigo-500"}`}
                      style={{ width: `${row.requests > 0 ? Math.max(4, share) : 0}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Usage Logs & Latest Conversations */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-7 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-2.5 shadow-xs dark:shadow-none">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
            Recent Telemetry Runs
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-1.5 pr-3">Tier</th>
                  <th className="py-1.5 pr-3">Task</th>
                  <th className="py-1.5 pr-3">Latency</th>
                  <th className="py-1.5 pr-3">Credits</th>
                  <th className="py-1.5">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                {recentLogs.map((log) => (
                  <tr key={log.id} className="text-slate-700 dark:text-slate-200">
                    <td className="py-1.5 pr-3 font-mono uppercase text-[11px]">{log.model_tier}</td>
                    <td className="py-1.5 pr-3 font-mono uppercase text-[11px]">{log.task_type}</td>
                    <td className="py-1.5 pr-3 font-mono">{log.latency_ms} ms</td>
                    <td className="py-1.5 pr-3 font-mono text-amber-700 dark:text-amber-300">-{formatCreditsBdtUsd(log.credits_consumed, { compact: true })}</td>
                    <td className="py-1.5 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                      {log.created_at.slice(0, 19).replace("T", " ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!recentLogs.length && (
              <p className="text-xs text-slate-500 py-5 text-center">No inference runs recorded yet.</p>
            )}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-2.5 shadow-xs dark:shadow-none">
          <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
            Recent Conversations
          </h3>
          <div className="space-y-1.5">
            {conversations.slice(0, 6).map((conv) => (
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
                <span className="text-[11px] font-semibold text-indigo-600 dark:text-cyan-400 shrink-0">Open</span>
              </button>
            ))}
            {!conversations.length && (
              <p className="text-xs text-slate-500 py-5 text-center">No saved threads yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

