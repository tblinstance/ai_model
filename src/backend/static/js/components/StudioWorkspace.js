/**
 * Vue 3 CDN Studio Workspace for multi-turn Conversations across Chat, Images, Video, and Code.
 */
window.StudioWorkspaceComponent = {
  props: [
    "store",
    "onRunTask",
    "onRunAgent",
    "onSelectConversation",
    "onNewConversation",
    "onDeleteConversation",
    "onAttachMedia",
  ],
  template: `
    <section class="glass-panel rounded-2xl p-5 flex flex-col gap-4">
      <!-- Saved Conversation Threads Bar -->
      <div class="flex flex-wrap items-center justify-between gap-2 bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5">
        <div class="flex items-center gap-2 overflow-x-auto flex-1 min-w-0">
          <button
            type="button"
            @click="onNewConversation && onNewConversation()"
            class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shrink-0 flex items-center gap-1"
          >
            <i data-lucide="plus" class="w-3.5 h-3.5"></i>
            <span>New Chat</span>
          </button>

          <div
            v-for="conv in store.conversations"
            :key="'conv-' + conv.id"
            @click="onSelectConversation && onSelectConversation(conv.id)"
            class="px-2.5 py-1 rounded-lg text-xs border cursor-pointer flex items-center gap-1.5 shrink-0 max-w-[200px] transition"
            :class="store.activeConversation?.id === conv.id ? 'bg-indigo-50 dark:bg-indigo-500/20 border-indigo-300 dark:border-indigo-500/40 text-indigo-800 dark:text-indigo-200 font-semibold' : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:border-slate-300'"
          >
            <span class="truncate">{{ conv.title }}</span>
            <span class="text-[10px] font-mono opacity-70">({{ conv.message_count }})</span>
            <button
              type="button"
              @click.stop="onDeleteConversation && onDeleteConversation(conv.id)"
              class="text-slate-400 hover:text-rose-500 ml-0.5"
              title="Delete thread"
            >
              <i data-lucide="x" class="w-3 h-3"></i>
            </button>
          </div>
        </div>
        <span class="text-[11px] font-mono text-slate-500 shrink-0">
          {{ store.activeConversation ? ('Thread #' + store.activeConversation.id) : 'New Thread' }}
        </span>
      </div>

      <!-- Task Switcher Bar -->
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="store.activeTask = tab.id"
            class="px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition"
            :class="store.activeTask === tab.id ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/25' : 'bg-slate-100 dark:bg-slate-900/70 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'"
          >
            <i :data-lucide="tab.icon" class="w-3.5 h-3.5"></i>
            <span>{{ tab.label }}</span>
          </button>
        </div>
        <div v-if="store.activeTask === 'video'" class="flex items-center gap-2 text-xs">
          <span class="text-slate-600 dark:text-slate-400">MP4 Duration:</span>
          <select v-model.number="store.videoDurationSeconds" class="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2 py-1 text-slate-900 dark:text-slate-200">
            <option :value="600">10 min (min)</option>
            <option :value="720">12 min</option>
            <option :value="900">15 min</option>
            <option :value="1200">20 min</option>
            <option :value="1800">30 min</option>
          </select>
        </div>
        <div v-if="store.activeTask === 'code'" class="flex items-center gap-2 text-xs">
          <span class="text-slate-600 dark:text-slate-400">Language:</span>
          <select v-model="store.language" class="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-2 py-1 text-slate-900 dark:text-slate-200">
            <option value="python">Python</option>
            <option value="typescript">TypeScript</option>
            <option value="sql">SQL</option>
            <option value="bash">Bash</option>
          </select>
        </div>
      </div>

      <!-- Output / Conversation Transcript Area (Top / Middle) -->
      <div v-if="store.activeConversation?.messages?.length" class="space-y-3 min-h-[240px] max-h-[460px] overflow-y-auto custom-scroll pr-1">
        <div
          v-for="msg in store.activeConversation.messages"
          :key="'m-' + msg.id"
          class="rounded-xl p-4 space-y-2.5 border"
          :class="msg.role === 'user' ? 'bg-indigo-50/70 dark:bg-indigo-950/35 border-indigo-200 dark:border-indigo-500/30 ml-4' : 'bg-slate-50 dark:bg-slate-900/75 border-slate-200 dark:border-slate-800 mr-2'"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div class="flex items-center gap-2">
              <span class="font-semibold capitalize text-slate-900 dark:text-white">{{ msg.role }}</span>
              <span class="px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 font-mono uppercase text-[10px]">{{ msg.tier }} · {{ msg.task }}</span>
              <span v-if="msg.intent" class="px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[10px]">{{ msg.intent }}</span>
            </div>
            <div v-if="msg.role !== 'user'" class="text-slate-600 dark:text-slate-400 font-mono">
              {{ msg.backend_used }} · {{ msg.latency_ms }} ms · -{{ formatCreditsBdtUsd(msg.credits_used, { compact: true }) }}
            </div>
          </div>

          <p v-if="msg.content" class="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">{{ msg.content }}</p>

          <pre v-if="msg.code" class="code-surface rounded-xl p-3 text-xs text-cyan-800 dark:text-cyan-200 overflow-x-auto"><code>{{ msg.code }}</code></pre>

          <div v-if="msg.preview_base64 || msg.artifact_url" class="pt-1 space-y-1.5">
            <video
              v-if="isVideoArtifact(msg)"
              controls
              playsinline
              preload="metadata"
              :src="resolveMediaUrl(msg)"
              class="rounded-xl max-h-72 w-full max-w-md border border-slate-300 dark:border-slate-700/70 bg-black"
            >
              <source :src="resolveMediaUrl(msg)" type="video/mp4" />
              Your browser does not support MP4 video playback.
            </video>
            <img
              v-else
              :src="resolveMediaUrl(msg)"
              alt="AI Generated Output"
              class="rounded-xl max-h-72 border border-slate-300 dark:border-slate-700/70 object-contain bg-slate-900/5 dark:bg-black/40"
            />
            <div>
              <a
                :href="resolveMediaUrl(msg)"
                :download="'tblinc-generated.' + mediaExtension(msg)"
                :target="isVideoArtifact(msg) ? '_blank' : null"
                class="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-700 dark:text-cyan-300 hover:underline"
              >
                Download .{{ mediaExtension(msg) }}
              </a>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="space-y-3 min-h-[240px] max-h-[460px] overflow-y-auto custom-scroll pr-1">
        <div
          v-for="item in [...store.outputs].reverse()"
          :key="item.request_id"
          class="rounded-xl bg-slate-50 dark:bg-slate-900/75 border border-slate-200 dark:border-slate-800 p-4 space-y-2.5"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 font-mono uppercase">{{ item.tier }}</span>
              <span class="px-2 py-0.5 rounded-md bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 font-mono uppercase">{{ item.task }}</span>
              <span class="text-slate-600 dark:text-slate-400">{{ item.diagnostics?.backend_used }}</span>
            </div>
            <div class="text-slate-600 dark:text-slate-400 font-mono">
              {{ item.diagnostics?.latency_ms }} ms · -{{ formatCreditsBdtUsd(item.credits_used, { compact: true }) }}
            </div>
          </div>

          <div v-if="item.extra?.fallback_reason" class="text-[11px] font-mono text-amber-700 dark:text-amber-300/90 bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/25 rounded-lg px-2.5 py-1.5">
            {{ item.extra.fallback_reason }}
          </div>

          <p v-if="item.text" class="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed">{{ item.text }}</p>

          <pre v-if="item.code" class="code-surface rounded-xl p-3 text-xs text-cyan-800 dark:text-cyan-200 overflow-x-auto"><code>{{ item.code }}</code></pre>

          <div v-if="item.preview_base64 || item.artifact_url" class="pt-1 space-y-1.5">
            <video
              v-if="isVideoArtifact(item)"
              controls
              playsinline
              preload="metadata"
              :poster="item.extra?.poster_data_url || null"
              :src="resolveMediaUrl(item)"
              class="rounded-xl max-h-72 w-full max-w-md border border-slate-300 dark:border-slate-700/70 bg-black"
            >
              <source :src="resolveMediaUrl(item)" type="video/mp4" />
              Your browser does not support MP4 video playback.
            </video>
            <img
              v-else
              :src="resolveMediaUrl(item)"
              alt="AI Generated Output"
              class="rounded-xl max-h-72 border border-slate-300 dark:border-slate-700/70 object-contain bg-slate-900/5 dark:bg-black/40"
            />
            <div>
              <a
                :href="resolveMediaUrl(item)"
                :download="'tblinc-generated.' + mediaExtension(item)"
                :target="isVideoArtifact(item) ? '_blank' : null"
                class="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-700 dark:text-cyan-300 hover:underline"
              >
                Download .{{ mediaExtension(item) }}
              </a>
            </div>
          </div>
        </div>

        <div v-if="!store.outputs.length" class="text-center py-10 text-xs text-slate-500 rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
          No outputs yet. Choose Chat, Images, Video, or Code and enter a prompt below.
        </div>
      </div>

        <!-- Prompt Input Form (Bottom) -->
      <div class="flex flex-col gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
        <input
          v-model="store.systemPrompt"
          type="text"
          placeholder="Optional system instruction (e.g., Reply concisely as a senior engineer)..."
          class="w-full rounded-xl bg-slate-50 dark:bg-slate-950/75 border border-slate-200 dark:border-slate-800 px-3.5 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:border-cyan-500 focus:outline-none"
        />

        <div v-if="store.studioAttachment" class="flex items-center justify-between gap-3 rounded-xl bg-slate-50 dark:bg-slate-950/85 border border-cyan-200 dark:border-cyan-500/35 px-3 py-2">
          <div class="flex items-center gap-3 min-w-0">
            <img :src="store.studioAttachment.previewDataUrl" :alt="store.studioAttachment.filename" class="w-10 h-10 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shrink-0" />
            <div class="min-w-0">
              <div class="text-xs font-semibold text-slate-900 dark:text-white truncate">{{ store.studioAttachment.filename }}</div>
              <div class="text-[11px] font-mono text-cyan-700 dark:text-cyan-300">
                {{ store.studioAttachment.kind === 'video' ? ('Video · ' + store.studioAttachment.width + 'x' + store.studioAttachment.height + ' · ' + (store.studioAttachment.framesBase64?.length || 1) + ' frames') : ('Image · ' + store.studioAttachment.width + 'x' + store.studioAttachment.height) }}
              </div>
            </div>
          </div>
          <button type="button" @click="store.studioAttachment = null" class="text-xs text-slate-500 hover:text-rose-500 px-2 py-1">Remove</button>
        </div>

        <textarea
          v-model="store.prompt"
          rows="2"
          @keydown.enter.exact.prevent="(store.prompt.trim() || store.studioAttachment) && !store.loading && onRunTask()"
          :placeholder="promptPlaceholder"
          class="w-full rounded-xl bg-slate-50 dark:bg-slate-950/75 border border-slate-300 dark:border-slate-700/80 p-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
        ></textarea>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap gap-2">
            <label class="cursor-pointer px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 inline-flex items-center gap-1.5">
              <i data-lucide="image-plus" class="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400"></i>
              <span>Upload Image / Video</span>
              <input type="file" accept="image/*,video/*" @change="onPickMedia" class="hidden" />
            </label>
            <button
              type="button"
              @click="toggleVoiceMode"
              :class="store.voiceMode ? 'bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border-cyan-400 dark:border-cyan-500' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'"
              class="px-3 py-2 rounded-xl border text-xs font-semibold inline-flex items-center gap-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
              title="Voice Prompt Mode"
            >
              <i data-lucide="mic" class="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400"></i>
              <span>Voice</span>
            </button>
            <button
              type="button"
              @click="toggleLiveMode"
              :class="store.liveMode ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-400 dark:border-emerald-500' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'"
              class="px-3 py-2 rounded-xl border text-xs font-semibold inline-flex items-center gap-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 transition"
              title="Live Session Mode"
            >
              <i data-lucide="radio" class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400"></i>
              <span>Live</span>
            </button>
            <button
              @click="onRunTask"
              :disabled="store.loading || (!store.prompt.trim() && !store.studioAttachment)"
              class="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 text-white text-sm font-semibold hover:opacity-95 disabled:opacity-40 flex items-center gap-2"
            >
              <i data-lucide="sparkles" class="w-4 h-4"></i>
              <span>{{ store.loading ? 'Synthesizing...' : 'Generate (' + store.activeTier.toUpperCase() + ')' }}</span>
            </button>
            <button
              v-if="store.agents.length"
              @click="onRunAgent(store.agents[0].id)"
              :disabled="store.loading || !store.prompt.trim()"
              class="px-3.5 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-medium flex items-center gap-1.5 disabled:opacity-40"
            >
              <i data-lucide="bot" class="w-3.5 h-3.5 text-purple-600 dark:text-purple-400"></i>
              <span>Run via Agent</span>
            </button>
          </div>
          <span class="text-xs text-slate-600 dark:text-slate-400">
            {{ store.authenticated ? 'Enter to send · Shift+Enter for new line' : 'Sign in to consume quota & save history' }}
          </span>
        </div>
      </div>
    </section>
  `,
  setup(props) {
    const { computed } = Vue;
    const tabs = [
      { id: "chat", label: "tblinc Chat", icon: "message-square" },
      { id: "images", label: "tblinc Images", icon: "image" },
      { id: "video", label: "tblinc Video", icon: "film" },
      { id: "code", label: "tblinc Code", icon: "code-2" },
    ];
    const promptPlaceholder = computed(() => {
      const map = {
        chat: "Ask a question, voice && live, solve math, write code, or upload an image/video to analyze or generate...",
        voice: "Speak into microphone or enter a voice prompt, live audio transcript, or spoken request...",
        live: "Stream real-time live video/audio, interactive live session, or multi-modal live prompt...",
        images: "Describe a visual artwork to render, or upload an image/video frame to restyle...",
        video: "Describe an H.264 MP4 sequence (Tblinc Ai), or upload media to animate...",
        code: "Describe a function, API, script, or query to generate in Python, TypeScript, SQL, or Bash...",
      };
      if (props.store?.voiceMode) return map.voice;
      if (props.store?.liveMode) return map.live;
      return map[props.store.activeTask] || map.chat;
    });
    const toggleVoiceMode = () => {
      props.store.voiceMode = !props.store.voiceMode;
      if (props.store.voiceMode) props.store.liveMode = false;
      if (window.lucide) setTimeout(() => window.lucide.createIcons(), 50);
    };
    const toggleLiveMode = () => {
      props.store.liveMode = !props.store.liveMode;
      if (props.store.liveMode) props.store.voiceMode = false;
      if (window.lucide) setTimeout(() => window.lucide.createIcons(), 50);
    };
    const isVideoArtifact = (entry) => {
      if (!entry) return false;
      const mime = String(entry.mime_type || "").toLowerCase();
      const url = String(entry.artifact_url || "").toLowerCase();
      return mime.startsWith("video/") || url.endsWith(".mp4");
    };
    const resolveMediaUrl = (entry) => {
      if (!entry) return "";
      const rawUrl = entry.artifact_url ? String(entry.artifact_url).trim() : "";
      if (isVideoArtifact(entry)) {
        if (rawUrl) {
          if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://") || rawUrl.startsWith("//")) {
            return rawUrl;
          }
          if (rawUrl.startsWith("/")) {
            return rawUrl;
          }
          return (props.store?.fastapiBaseUrl || "") + "/" + rawUrl;
        }
        return entry.preview_base64
          ? "data:" + (entry.mime_type || "video/mp4") + ";base64," + entry.preview_base64
          : "";
      }
      if (entry.preview_base64) {
        return "data:" + (entry.mime_type || "image/png") + ";base64," + entry.preview_base64;
      }
      if (rawUrl) {
        if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://") || rawUrl.startsWith("//")) {
          return rawUrl;
        }
        if (rawUrl.startsWith("/")) {
          return rawUrl;
        }
        return (props.store?.fastapiBaseUrl || "") + "/" + rawUrl;
      }
      return "";
    };
    const mediaExtension = (entry) => {
      if (isVideoArtifact(entry)) return "mp4";
      const mime = String(entry?.mime_type || "").toLowerCase();
      if (mime.includes("gif")) return "gif";
      if (mime.includes("webp")) return "webp";
      if (mime.includes("jpeg")) return "jpg";
      return "png";
    };
    const onPickMedia = async (e) => {
      const file = e && e.target && e.target.files ? e.target.files[0] : null;
      if (file && props.onAttachMedia) {
        await props.onAttachMedia(file);
      }
      if (e && e.target) e.target.value = "";
    };
    const formatCreditsBdtUsd = (c, opts) => window.AIModelBilling.formatCreditsBdtUsd(c, opts);
    return {
      tabs,
      promptPlaceholder,
      isVideoArtifact,
      resolveMediaUrl,
      mediaExtension,
      onPickMedia,
      formatCreditsBdtUsd,
      toggleVoiceMode,
      toggleLiveMode,
    };
  },
};
