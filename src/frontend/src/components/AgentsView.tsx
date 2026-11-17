import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Bot, Play, Plus } from "lucide-react";
import { formatCreditsBdtUsd } from "../services/payment";
import {
  AgentProfile,
  AgentRunItem,
  ModelTier,
  TaskType,
} from "../types/ai";

interface AgentsViewProps {
  agents: AgentProfile[];
  runs: AgentRunItem[];
  activeTier: ModelTier;
  authenticated: boolean;
  onCreateAgent: (payload: {
    name: string;
    system_prompt: string;
    default_tier: ModelTier;
    default_task: TaskType;
  }) => Promise<void>;
  onExecuteAgent: (agentId: number, prompt: string, tier: ModelTier) => Promise<void>;
  onOpenAuth: () => void;
}

export function AgentsView({
  agents,
  runs,
  activeTier,
  authenticated,
  onCreateAgent,
  onExecuteAgent,
  onOpenAuth,
}: AgentsViewProps) {
  const [name, setName] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("You are a specialized AI-Model engineering agent.");
  const [tier, setTier] = useState<ModelTier>(activeTier);
  const [task, setTask] = useState<TaskType>("chat");
  const [runPrompt, setRunPrompt] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    setTier(activeTier);
  }, [activeTier]);

  if (!authenticated) {
    return (
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center space-y-3 shadow-xs dark:shadow-none">
        <Bot className="w-10 h-10 text-purple-600 dark:text-purple-400 mx-auto" />
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Sign In to Manage Agents</h2>
        <p className="text-xs text-slate-600 dark:text-slate-400">
          Create custom personas connected to Flash, Pro, and Advance pipelines.
        </p>
        <button
          onClick={onOpenAuth}
          className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold"
        >
          Sign In with Djoser
        </button>
      </div>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await onCreateAgent({ name, system_prompt: systemPrompt, default_tier: tier, default_task: task });
    setName("");
  };

  const handleRun = async (agent: AgentProfile) => {
    if (!runPrompt.trim() || running) return;
    setRunning(true);
    setSelectedAgentId(agent.id);
    try {
      await onExecuteAgent(agent.id, runPrompt, activeTier);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <form
          onSubmit={handleCreate}
          className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3 shadow-xs dark:shadow-none"
        >
          <h2 className="font-display font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <Plus className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>Create Custom Agent</span>
          </h2>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Agent name (e.g. Vision Shader Agent)"
            className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-white"
          />
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={2}
            className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-xs text-slate-800 dark:text-slate-200"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value as ModelTier)}
              className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
            >
              <option value="flash">Flash Tier</option>
              <option value="pro">Pro Tier</option>
              <option value="advance">Advance Tier</option>
            </select>
            <select
              value={task}
              onChange={(e) => setTask(e.target.value as TaskType)}
              className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white"
            >
              <option value="chat">Chat</option>
              <option value="code">Code</option>
              <option value="images">Images</option>
              <option value="video">Video</option>
            </select>
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
          >
            Save Agent Profile
          </button>
        </form>

        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between gap-2">
            <h2 className="font-display font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Bot className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span>Execute an Agent</span>
            </h2>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-cyan-300 uppercase">
              Active: {activeTier}
            </span>
          </div>
          <input
            value={runPrompt}
            onChange={(e) => setRunPrompt(e.target.value)}
            placeholder="Enter prompt for the selected agent..."
            className="w-full rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-white"
          />
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {agents.map((ag) => (
              <motion.div
                key={ag.id}
                whileHover={{ x: 2 }}
                className="rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 p-3 flex items-center justify-between gap-3"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-900 dark:text-white">{ag.name}</div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-400 font-mono">
                    {ag.default_tier} · {ag.default_task}
                  </div>
                </div>
                <button
                  disabled={running || !runPrompt.trim()}
                  onClick={() => handleRun(ag)}
                  className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-40"
                >
                  <Play className="w-3 h-3" />
                  <span>{running && selectedAgentId === ag.id ? "Running..." : "Run"}</span>
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3 shadow-xs dark:shadow-none">
        <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white">Recent Agent Runs</h3>
        <div className="space-y-2">
          {runs.map((run) => (
            <div key={run.id} className="rounded-xl bg-slate-50 dark:bg-slate-950/75 border border-slate-200 dark:border-slate-800 p-3 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-indigo-700 dark:text-indigo-300">{run.agent_name}</span>
                <span className="font-mono text-slate-600 dark:text-slate-400">
                  {run.selected_tier}/{run.selected_task} · -{formatCreditsBdtUsd(run.credits_used, { compact: true })} · {run.latency_ms} ms
                </span>
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-300">{run.prompt}</p>
              {run.response_text && (
                <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">{run.response_text}</p>
              )}
            </div>
          ))}
          {!runs.length && <p className="text-xs text-slate-500">No agent runs recorded yet.</p>}
        </div>
      </div>
    </div>
  );
}

