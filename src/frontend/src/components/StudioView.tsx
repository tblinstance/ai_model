import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Bot,
  Check,
  Code2,
  Copy,
  Download,
  Film,
  Image as ImageIcon,
  ImagePlus,
  MessageSquare,
  Mic,
  Plus,
  Radio,
  Send,
  Settings2,
  Sparkles,
  Trash2,
  User,
  X,
} from "lucide-react";
import { FASTAPI_URL } from "../services/http";
import { formatCreditsBdtUsd } from "../services/payment";
import {
  attachmentToMetadata,
  prepareMediaAttachment,
  UploadedMediaAttachment,
} from "../utils/mediaUpload";
import {
  ConversationDetail,
  ConversationSummary,
  GenerationResponse,
  ModelSummary,
  ModelTier,
  TaskType,
} from "../types/ai";

interface StudioViewProps {
  activeTier: ModelTier;
  activeTask: TaskType;
  onSelectTask: (task: TaskType) => void;
  models: ModelSummary[];
  outputs: GenerationResponse[];
  conversations: ConversationSummary[];
  activeConversation: ConversationDetail | null;
  loading: boolean;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => Promise<void> | void;
  onDeleteConversation: (id: number) => void;
  onGenerate: (
    prompt: string,
    language?: string,
    systemPrompt?: string,
    metadata?: Record<string, unknown>,
    taskOverride?: TaskType,
    durationSeconds?: number
  ) => Promise<void>;
}

const TASKS: Array<{ id: TaskType; label: string; icon: typeof MessageSquare; hint: string }> = [
  {
    id: "chat",
    label: "tblinc Chat",
    icon: MessageSquare,
    hint: "Ask a question, voice && live, solve math, write code, or upload an image/video to restyle or generate...",
  },
  {
    id: "images",
    label: "tblinc Images",
    icon: ImageIcon,
    hint: "Describe a visual artwork to render, or upload an image/video frame to transform...",
  },
  {
    id: "video",
    label: "tblinc Video",
    icon: Film,
    hint: "Describe an H.264 MP4 sequence (orbit, ripple, vortex, sweep), or upload media to animate...",
  },
  {
    id: "code",
    label: "tblinc Code",
    icon: Code2,
    hint: "Describe a function, API, script, or query to generate in Python, TypeScript, SQL, or Bash...",
  },
  {
    id: "audio",
    label: "tblinc Audio",
    icon: Mic,
    hint: "Enter text to synthesize neural speech (Edge-TTS), transcribe with Whisper, or acoustic analysis...",
  },
  {
    id: "rag",
    label: "tblinc Knowledge",
    icon: Sparkles,
    hint: "Query dense semantic vector memory (ChromaDB) or scrape URLs for live knowledge retrieval...",
  },
];

export function StudioView({
  activeTier,
  activeTask,
  onSelectTask,
  models,
  outputs,
  conversations,
  activeConversation,
  loading,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onGenerate,
}: StudioViewProps) {
  const [prompt, setPrompt] = useState("");
  const [language, setLanguage] = useState("python");
  const [videoDurationSeconds, setVideoDurationSeconds] = useState(600);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [attachment, setAttachment] = useState<UploadedMediaAttachment | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [liveMode, setLiveMode] = useState(false);
  const promptInputRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const activeModel = models.find((m) => m.tier === activeTier);
  const currentTaskMeta = TASKS.find((t) => t.id === activeTask)!;
  const threadMessages = activeConversation?.messages || [];

  const promptPlaceholder = useMemo(() => {
    if (voiceMode) {
      return "Speak or enter a voice prompt, live audio transcript, or real-time voice command...";
    }
    if (liveMode) {
      return "Stream real-time live video/audio, interactive live session, or multi-modal live prompt...";
    }
    const map: Record<string, string> = {
      chat: "Ask a question, voice && live, solve math, write code, or upload an image/video to restyle or generate...",
      voice: "Speak or enter a voice prompt, live audio transcript, or real-time voice command...",
      live: "Stream real-time live video/audio, interactive live session, or multi-modal live prompt...",
      images: "Describe a visual artwork to render, or upload an image/video frame to transform...",
      video: "Describe an H.264 MP4 sequence (orbit, ripple, vortex, sweep), or upload media to animate...",
      code: "Describe a function, API, script, or query to generate in Python, TypeScript, SQL, or Bash...",
    };
    return map[activeTask] || currentTaskMeta?.hint || map.chat;
  }, [activeTask, currentTaskMeta, voiceMode, liveMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [threadMessages.length, outputs.length, activeConversation?.id]);

  const attachMediaFile = async (file: File | undefined | null) => {
    if (!file) return;
    setUploadError("");
    try {
      const prepared = await prepareMediaAttachment(file);
      setAttachment(prepared);
      promptInputRef.current?.focus();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Could not attach media file.");
    }
  };

  const submitPrompt = async () => {
    const trimmed = prompt.trim();
    if ((!trimmed && !attachment) || loading) return;
    const defaultPrompt =
      attachment?.kind === "video" || activeTask === "video"
        ? "Generate animated video from uploaded media"
        : "Generate styled artwork from uploaded media";
    const currentPrompt = trimmed || defaultPrompt;
    const metadata = attachment ? attachmentToMetadata(attachment) : undefined;
    setPrompt("");
    setAttachment(null);
    setUploadError("");
    await onGenerate(
      currentPrompt,
      activeTask === "code" ? language : undefined,
      systemPrompt.trim() || undefined,
      metadata,
      undefined,
      activeTask === "video" ? videoDurationSeconds : undefined
    );
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/") || item.type.startsWith("video/")) {
        const pastedFile = item.getAsFile();
        if (pastedFile) {
          e.preventDefault();
          void attachMediaFile(pastedFile);
          break;
        }
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await submitPrompt();
  };

  const handlePromptKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      await submitPrompt();
    }
  };

  const handleCreateNew = async () => {
    await onNewConversation();
    promptInputRef.current?.focus();
  };

  const copyCode = async (id: string, code: string) => {
    await navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const renderCodeBlock = (blockId: string, code: string) => (
    <div className="relative rounded-xl bg-slate-50 dark:bg-slate-950 border border-cyan-200 dark:border-cyan-500/20 p-4">
      <button
        type="button"
        onClick={() => copyCode(blockId, code)}
        className="absolute top-2.5 right-2.5 p-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300"
        title="Copy code"
      >
        {copiedId === blockId ? (
          <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
      <pre className="text-xs text-cyan-800 dark:text-cyan-200 overflow-x-auto pr-8">
        <code>{code}</code>
      </pre>
    </div>
  );

  const renderMedia = (
    previewBase64?: string | null,
    mimeType?: string | null,
    artifactUrl?: string | null,
    extra?: Record<string, unknown>
  ) => {
    if (!previewBase64 && !artifactUrl) return null;
    const isAudio =
      (mimeType || "").toLowerCase().startsWith("audio/") ||
      (artifactUrl || "").toLowerCase().endsWith(".mp3") ||
      (artifactUrl || "").toLowerCase().endsWith(".wav") ||
      (artifactUrl || "").toLowerCase().endsWith(".ogg") ||
      (artifactUrl || "").toLowerCase().endsWith(".flac");
    const isVideo =
      (mimeType || "").toLowerCase().startsWith("video/") ||
      (artifactUrl || "").toLowerCase().endsWith(".mp4");
    const resolvedUrl = artifactUrl
      ? artifactUrl.startsWith("http://") || artifactUrl.startsWith("https://") || artifactUrl.startsWith("//")
        ? artifactUrl
        : artifactUrl.startsWith("/")
          ? artifactUrl
          : `${FASTAPI_URL}/${artifactUrl}`
      : "";
    const src = (isVideo || isAudio)
      ? resolvedUrl || (previewBase64 ? `data:${mimeType || (isAudio ? "audio/mpeg" : "video/mp4")};base64,${previewBase64}` : "")
      : previewBase64
        ? `data:${mimeType || "image/png"};base64,${previewBase64}`
        : resolvedUrl;
    if (!src) return null;
    const ext = isAudio
      ? (artifactUrl || "").endsWith(".wav") ? "wav" : "mp3"
      : isVideo
        ? "mp4"
        : (mimeType || "").includes("gif")
          ? "gif"
          : (mimeType || "").includes("webp")
            ? "webp"
            : (mimeType || "").includes("jpeg")
              ? "jpg"
              : "png";
    const posterUrl = typeof extra?.poster_data_url === "string" ? extra.poster_data_url : undefined;
    return (
      <div className="pt-1 space-y-1.5">
        {isAudio ? (
          <div className="p-3 bg-slate-100 dark:bg-slate-950/80 border border-slate-300 dark:border-slate-800 rounded-xl space-y-2 max-w-md">
            <div className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-2">
              <Mic className="w-3.5 h-3.5 text-cyan-500" />
              <span>Neural Audio ({ext.toUpperCase()})</span>
            </div>
            <audio controls preload="metadata" src={src} className="w-full h-8">
              Your browser does not support audio playback.
            </audio>
          </div>
        ) : isVideo ? (
          <video
            controls
            playsInline
            preload="metadata"
            poster={posterUrl}
            src={src}
            className="rounded-xl max-h-80 w-full max-w-lg border border-slate-300 dark:border-slate-700/70 bg-black"
          >
            <source src={src} type="video/mp4" />
            Your browser does not support MP4 playback.
          </video>
        ) : (
          <img
            src={src}
            alt="Generated neural visual"
            className="rounded-xl max-h-80 border border-slate-300 dark:border-slate-700/70 bg-slate-900/5 dark:bg-black/50 object-contain"
          />
        )}
        <div>
          <a
            href={src}
            download={`tblinc-generated.${ext}`}
            target={isVideo ? "_blank" : undefined}
            rel={isVideo ? "noopener noreferrer" : undefined}
            className="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-700 dark:text-cyan-300 hover:underline"
          >
            <Download className="w-3 h-3" />
            <span>Download .{ext}</span>
          </a>
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
      {/* Persistent Conversations Sidebar */}
      <aside className="xl:col-span-3 bg-white/90 dark:bg-slate-900/65 backdrop-blur-xl border border-slate-200 dark:border-slate-800/80 rounded-2xl p-4 flex flex-col gap-3 shadow-xs dark:shadow-none xl:h-[calc(100vh-8.5rem)]">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="font-display font-semibold text-sm text-slate-900 dark:text-white">
              Conversations
            </h2>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              {conversations.length} saved thread{conversations.length === 1 ? "" : "s"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleCreateNew()}
            className="px-2.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 max-h-60 xl:max-h-none pr-1">
          {conversations.length === 0 ? (
            <div className="rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-dashed border-slate-200 dark:border-slate-800 p-3 text-[11px] text-slate-500 dark:text-slate-400 text-center">
              Click New or send a prompt below to create your first persistent thread.
            </div>
          ) : (
            conversations.map((conv) => {
              const selected = activeConversation?.id === conv.id;
              return (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={`group rounded-xl p-2.5 border cursor-pointer transition flex items-start justify-between gap-2 ${
                    selected
                      ? "bg-indigo-50 dark:bg-indigo-500/15 border-indigo-200 dark:border-indigo-500/40"
                      : "bg-slate-50/70 dark:bg-slate-950/50 border-slate-200/80 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                      {conv.title}
                    </div>
                    <div className="flex items-center gap-1.5 mt-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                      <span className="uppercase">{conv.tier}</span>
                      <span>·</span>
                      <span className="uppercase">{conv.task}</span>
                      <span>·</span>
                      <span>{conv.message_count} msgs</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteConversation(conv.id);
                    }}
                    title="Delete conversation"
                    className="p-1 rounded-lg text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 opacity-80 group-hover:opacity-100 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* Main Chat Workspace: Header (top) -> Output Thread (middle) -> Prompt Input (bottom) */}
      <div className="xl:col-span-9 flex flex-col gap-4 xl:h-[calc(100vh-8.5rem)]">
        {/* Top Model & Modality Bar */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="shrink-0 bg-white/90 dark:bg-slate-900/65 backdrop-blur-xl border border-slate-200 dark:border-slate-800/80 rounded-2xl p-4 space-y-3 shadow-xs dark:shadow-none"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="font-display text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
                <span>
                  {activeModel?.display_name ||
                    `tblinc ${activeTier.charAt(0).toUpperCase()}${activeTier.slice(1)}`}
                </span>
                {activeConversation && (
                  <span className="text-xs font-mono font-normal px-2 py-0.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 truncate max-w-xs">
                    #{activeConversation.id} · {activeConversation.title}
                  </span>
                )}
              </h1>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                {activeModel?.description ||
                  "tblinc AI — multimodal multi-turn workspace across Chat, Images, Video, and Code."}
              </p>
            </div>
            {activeModel && (
              <div className="text-xs font-mono px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-cyan-700 dark:text-cyan-300">
                Cost: {formatCreditsBdtUsd(activeModel.credit_cost[activeTask], { compact: true })} · {activeModel.parameter_estimate.toLocaleString()} params
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-t border-slate-200 dark:border-slate-800">
            <div className="flex flex-wrap gap-2">
              {TASKS.map((tab) => {
                const Icon = tab.icon;
                const active = activeTask === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => onSelectTask(tab.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition ${
                      active
                        ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/25"
                        : "bg-slate-100 dark:bg-slate-950/70 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowSystemPrompt((prev) => !prev)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 border transition ${
                  showSystemPrompt || systemPrompt
                    ? "bg-cyan-50 dark:bg-cyan-500/15 border-cyan-200 dark:border-cyan-500/40 text-cyan-700 dark:text-cyan-300"
                    : "bg-slate-100 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
                }`}
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>System Context</span>
              </button>

              {activeTask === "video" && (
                <select
                  value={videoDurationSeconds}
                  onChange={(e) => setVideoDurationSeconds(Number(e.target.value))}
                  title="Minimum 10 minutes MP4 duration"
                  className="bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-200"
                >
                  <option value={600}>10 min MP4 (min)</option>
                  <option value={720}>12 min MP4</option>
                  <option value={900}>15 min MP4</option>
                  <option value={1200}>20 min MP4</option>
                  <option value={1800}>30 min MP4</option>
                </select>
              )}

              {activeTask === "code" && (
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-slate-200"
                >
                  <option value="python">Python</option>
                  <option value="typescript">TypeScript</option>
                  <option value="sql">SQL</option>
                  <option value="bash">Bash</option>
                </select>
              )}
            </div>
          </div>

          {showSystemPrompt && (
            <input
              type="text"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="Optional system instruction (e.g., Answer concisely with bullet points)..."
              className="w-full rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-300 dark:border-slate-800 px-3.5 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
            />
          )}
        </motion.div>

        {/* Scrollable Conversation & Output Area (Top / Middle) */}
        <div className="flex-1 min-h-[260px] overflow-y-auto space-y-3 pr-1">
          {threadMessages.length > 0 ? (
            threadMessages.map((msg) => {
              const isUser = msg.role === "user";
              const msgKey = `msg-${msg.id}`;
              return (
                <motion.div
                  key={msgKey}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`rounded-2xl p-4 border space-y-2.5 ${
                    isUser
                      ? "bg-indigo-50/80 dark:bg-indigo-950/35 border-indigo-200 dark:border-indigo-500/30 ml-0 sm:ml-10"
                      : "bg-white/95 dark:bg-slate-900/75 border-slate-200 dark:border-slate-800 mr-0 sm:mr-6"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2">
                      {isUser ? (
                        <User className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                      ) : (
                        <Bot className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                      )}
                      <span className="font-semibold text-slate-900 dark:text-white capitalize">
                        {msg.role}
                      </span>
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 font-mono text-[10px] uppercase text-slate-700 dark:text-slate-300">
                        {msg.tier} · {msg.task}
                      </span>
                      {msg.intent && (
                        <span className="px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-500/15 font-mono text-[10px] text-emerald-700 dark:text-emerald-300">
                          {msg.intent}
                        </span>
                      )}
                    </div>
                    {!isUser && (
                      <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                        {msg.latency_ms} ms · -{formatCreditsBdtUsd(msg.credits_used, { compact: true })}
                      </div>
                    )}
                  </div>

                  {msg.content && (
                    <p className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </p>
                  )}

                  {msg.code && renderCodeBlock(msgKey, msg.code)}
                  {renderMedia(msg.preview_base64, msg.mime_type, msg.artifact_url)}
                </motion.div>
              );
            })
          ) : outputs.length > 0 ? (
            <AnimatePresence>
              {[...outputs].reverse().map((item) => (
                <motion.div
                  key={item.request_id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="bg-white/90 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 space-y-3 shadow-xs dark:shadow-none"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-lg bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 font-mono uppercase">
                        {item.tier}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-lg bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 font-mono uppercase">
                        {item.task}
                      </span>
                    </div>
                    <div className="text-slate-600 dark:text-slate-400 font-mono">
                      {item.diagnostics.latency_ms} ms · conf {item.diagnostics.confidence_score} · -{formatCreditsBdtUsd(item.credits_used, { compact: true })}
                    </div>
                  </div>

                  {item.text && (
                    <p className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {item.text}
                    </p>
                  )}

                  {item.code && renderCodeBlock(item.request_id, item.code)}
                  {renderMedia(item.preview_base64, item.mime_type, item.artifact_url, item.extra)}
                </motion.div>
              ))}
            </AnimatePresence>
          ) : (
            <div className="h-full min-h-[220px] rounded-2xl bg-white/60 dark:bg-slate-900/40 border border-dashed border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center p-6 text-center space-y-3">
              <Sparkles className="w-6 h-6 text-cyan-600 dark:text-cyan-400 opacity-80" />
              <div className="font-display font-semibold text-sm text-slate-800 dark:text-slate-200">
                {activeConversation
                  ? `Thread #${activeConversation.id} Ready`
                  : `tblinc ${activeTier.toUpperCase()} · ${currentTaskMeta.label}`}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md">
                {activeConversation
                  ? "Type a message or upload an image/video below to begin this conversation."
                  : "Enter a prompt or upload an image/video below to generate."}
              </p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Docked Chat Prompt Box with Image/Video Upload */}
        <form
          onSubmit={handleSubmit}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const dropped = e.dataTransfer?.files?.[0];
            if (dropped) void attachMediaFile(dropped);
          }}
          className={`shrink-0 bg-white/95 dark:bg-slate-900/80 backdrop-blur-xl border rounded-2xl p-4 space-y-3 shadow-xs dark:shadow-none transition ${
            dragOver
              ? "border-cyan-500 ring-2 ring-cyan-500/25"
              : "border-slate-200 dark:border-slate-800/80"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            onChange={(e) => {
              const selected = e.target.files?.[0];
              void attachMediaFile(selected);
              e.currentTarget.value = "";
            }}
            className="hidden"
          />

          {attachment && (
            <div className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 dark:bg-slate-950/90 border border-cyan-200 dark:border-cyan-500/35 px-3 py-2">
              <div className="flex items-center gap-3 min-w-0">
                <img
                  src={attachment.previewDataUrl}
                  alt={attachment.filename}
                  className="w-11 h-11 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shrink-0"
                />
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-900 dark:text-white truncate">
                    {attachment.filename}
                  </div>
                  <div className="text-[11px] font-mono text-cyan-700 dark:text-cyan-300">
                    {attachment.kind === "video"
                      ? `Video · ${attachment.width}x${attachment.height} · ${attachment.framesBase64?.length || 1} keyframes · ${attachment.durationSeconds ?? 1}s`
                      : `Image · ${attachment.width}x${attachment.height} · Ready to generate`}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAttachment(null)}
                title="Remove attachment"
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {uploadError && (
            <div className="text-xs text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 rounded-lg px-3 py-1.5">
              {uploadError}
            </div>
          )}

          <textarea
            ref={promptInputRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => void handlePromptKeyDown(e)}
            onPaste={handlePaste}
            rows={2}
            placeholder={promptPlaceholder}
            className="w-full rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-300 dark:border-slate-800 p-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 disabled:opacity-45 transition"
              >
                <ImagePlus className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>Upload Image / Video</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setVoiceMode((v) => !v);
                  setLiveMode(false);
                }}
                className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition ${
                  voiceMode
                    ? "bg-cyan-500/20 text-cyan-600 dark:text-cyan-300 border-cyan-400 dark:border-cyan-500/40"
                    : "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200"
                }`}
                title="Toggle Voice Mode"
              >
                <Mic className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
                <span>Voice</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setLiveMode((l) => !l);
                  setVoiceMode(false);
                }}
                className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition ${
                  liveMode
                    ? "bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border-emerald-400 dark:border-emerald-500/40"
                    : "bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200"
                }`}
                title="Toggle Live Mode"
              >
                <Radio className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Live</span>
              </button>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                {activeConversation
                  ? `Thread #${activeConversation.id} (${threadMessages.length} msgs) · Enter to send`
                  : "Enter to send · Paste or drop image/video"}
              </span>
            </div>
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              disabled={loading || (!prompt.trim() && !attachment)}
              type="submit"
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-600 text-white text-sm font-semibold flex items-center gap-2 disabled:opacity-45 shadow-lg shadow-indigo-600/25"
            >
              <Send className="w-4 h-4" />
              <span>{loading ? "Synthesizing..." : `Send (${activeTier.toUpperCase()})`}</span>
            </motion.button>
          </div>
        </form>
      </div>
    </div>
  );
}
