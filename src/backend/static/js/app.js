/**
 * Vue 3 CDN Application Bootstrap.
 */
(() => {
  const { computed, createApp, nextTick, onMounted, onUnmounted, onUpdated, ref, watch } = Vue;

  const app = createApp({
    components: {
      ModelSelector: window.ModelSelectorComponent,
      StudioWorkspace: window.StudioWorkspaceComponent,
      TrainingPanel: window.TrainingPanelComponent,
      BillingQuotaPanel: window.BillingQuotaPanelComponent,
      ProfilePanel: window.ProfilePanelComponent,
      SettingsPanel: window.SettingsPanelComponent,
      AdminControlPanel: window.AdminControlPanelComponent,
    },
    setup() {
      const store = window.createAIModelStore();
      const authForm = ref({ username: "", email: "", password: "", confirmPassword: "" });
      const topupAmount = ref(500);
      const modelTouchStartX = ref(null);

      const activeModelCard = computed(() => {
        const list = store.models || [];
        return list.find((m) => m.tier === store.activeTier) || list[0] || null;
      });

      const studioModes = [
        { id: "chat", label: "tblinc Chat", icon: "message-square", colorClass: "text-cyan-600 dark:text-cyan-400" },
        { id: "images", label: "tblinc Images", icon: "image", colorClass: "text-purple-600 dark:text-purple-400" },
        { id: "video", label: "tblinc Video", icon: "film", colorClass: "text-rose-600 dark:text-rose-400" },
        { id: "code", label: "tblinc Code", icon: "code-2", colorClass: "text-emerald-600 dark:text-emerald-400" },
      ];

      const portalHref = (section, opts = {}) => {
        if (!window.AIModelPortalRoute) return "/control/";
        return window.AIModelPortalRoute.buildPath(
          section,
          opts.task ?? store.activeTask,
          opts.settingsTab ?? store.settingsTab,
          window.location.pathname,
          opts.adminTab ?? store.adminTab
        );
      };

      const navigatePortal = (target, event = null) => {
        if (event && (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0)) {
          return;
        }
        if (event && typeof event.preventDefault === "function") {
          event.preventDefault();
        }
        if (target && target.task) store.activeTask = target.task;
        if (target && target.settingsTab) store.settingsTab = target.settingsTab;
        if (target && target.adminTab) store.adminTab = target.adminTab;
        if (target && target.section) store.activeSection = target.section;
        store.sidebarOpen = false;
      };

      const selectStudioTask = (task) => {
        navigatePortal({ section: "studio", task });
      };

      const sectionTitle = computed(() => {
        if (store.activeSection === "studio") {
          const mode = studioModes.find((m) => m.id === store.activeTask);
          return mode ? `tblinc AI · ${mode.label}` : "tblinc AI Studio";
        }
        if (store.activeSection === "admin") {
          const adminNames = {
            mfs: "MFS Approvals",
            users: "Users & Balances",
            invoices: "All Invoices",
            transactions: "All Transactions",
          };
          return `Admin · ${adminNames[store.adminTab] || "Control"}`;
        }
        if (store.activeSection === "settings") {
          const tabNames = {
            general: "General",
            keys: "API Keys",
            agents: "Agents",
            billing: "Billing & Quota",
            profiles: "Profiles",
            transactions: "Transactions",
            all: "All",
          };
          return `Settings · ${tabNames[store.settingsTab] || "General"}`;
        }
        const titles = {
          overview: "Overview",
          studio: "AI Studio",
          training: "Backend Neural Training",
          admin: "Users & Billing Control",
          settings: "Settings",
        };
        return titles[store.activeSection] || "AI Studio";
      });

      const toggleTheme = () => {
        const next = store.theme === "dark" ? "light" : "dark";
        store.theme = next;
        localStorage.setItem("theme", next);
        document.documentElement.classList.toggle("dark", next === "dark");
        document.documentElement.setAttribute("data-theme", next);
      };

      const toggleSidebar = () => {
        if (window.innerWidth < 1024) {
          store.sidebarOpen = !store.sidebarOpen;
          return;
        }
        store.sidebarCollapsed = !store.sidebarCollapsed;
        localStorage.setItem("sidebarCollapsed", String(store.sidebarCollapsed));
      };

      const openModelSwitcher = () => {
        if (store.sidebarCollapsed && window.innerWidth >= 1024) {
          store.sidebarCollapsed = false;
          localStorage.setItem("sidebarCollapsed", "false");
          store.modelDropdownOpen = true;
          return;
        }
        store.modelDropdownOpen = !store.modelDropdownOpen;
      };

      const selectProjectModel = (tier) => {
        if (!store.authenticated) {
          store.modelDropdownOpen = false;
          openAuth("login");
          return;
        }
        store.activeTier = tier;
        store.modelDropdownOpen = false;
        localStorage.setItem("ai_model_backend_active_tier", tier);
      };

      const stepModel = (delta) => {
        const list = store.models || [];
        if (!list.length) return;
        const idx = Math.max(0, list.findIndex((m) => m.tier === store.activeTier));
        const nextIdx = (idx + delta + list.length) % list.length;
        selectProjectModel(list[nextIdx].tier);
      };

      const onModelTouchStart = (evt) => {
        modelTouchStartX.value = evt.touches?.[0]?.clientX ?? null;
      };

      const onModelTouchEnd = (evt) => {
        if (modelTouchStartX.value === null) return;
        const endX = evt.changedTouches?.[0]?.clientX ?? modelTouchStartX.value;
        const diff = endX - modelTouchStartX.value;
        modelTouchStartX.value = null;
        if (Math.abs(diff) > 30) {
          stepModel(diff < 0 ? 1 : -1);
        }
      };

      const formatModelMeta = (model) => {
        const costs = model?.credit_cost ? Object.values(model.credit_cost).map(Number).filter(Number.isFinite) : [];
        const range = costs.length
          ? window.AIModelBilling.formatRangeBdtUsd(Math.min(...costs), Math.max(...costs))
          : window.AIModelBilling.formatRangeBdtUsd(1, 36);
        const layers = model?.num_layers ? `${model.num_layers}L` : "";
        const dim = model?.hidden_dim ? `${model.hidden_dim}d` : "";
        return [range, layers, dim].filter(Boolean).join(" · ");
      };

      const openAuth = (mode = "login") => {
        store.authMode = mode;
        store.authError = "";
        store.showPassword = false;
        store.showAuthModal = true;
      };

      const switchAuthMode = (mode) => {
        store.authMode = mode;
        store.authError = "";
        store.showPassword = false;
      };

      const refreshIcons = () => {
        if (window.lucide && typeof window.lucide.createIcons === "function") {
          window.lucide.createIcons();
        }
      };

      const loadPublicData = async () => {
        if (!store.authenticated) return;
        try {
          store.health = await window.AIModelAPI.getHealth();
        } catch (err) {
          console.warn("Health check error:", err);
        }
        try {
          store.plans = await window.AIModelAPI.getPlans();
        } catch (err) {
          console.warn("Plans error:", err);
        }
        try {
          const models = await window.AIModelAPI.getModels();
          if (Array.isArray(models) && models.length) {
            store.models = models;
          }
        } catch (err) {
          console.warn("Models error:", err);
        }
        try {
          if (typeof window.AIModelAPI.getTrainingStatus === "function") {
            store.trainingStatus = await window.AIModelAPI.getTrainingStatus();
          }
        } catch (err) {
          console.warn("Training status error:", err);
        }
      };

      const loadDashboard = async () => {
        if (!store.authenticated) return;
        try {
          const data = await window.AIModelAPI.getDashboard();
          if (!data.user || (!data.user.is_staff && !data.user.is_superuser)) {
            logout(true);
            store.authError = "Admin / staff privileges required on http://localhost:8000/. Members use http://127.0.0.1:5173.";
            return;
          }
          store.user = data.user;
          store.quota = data.quota;
          store.subscription = data.subscription;
          store.transactions = data.recent_transactions || [];
          store.verification = data.verification || null;
          store.models = data.models || [];
          store.agents = await window.AIModelAPI.getAgents();
          if (typeof window.AIModelAPI.getAgentRuns === "function") {
            store.agentRuns = await window.AIModelAPI.getAgentRuns();
          }
          if (typeof window.AIModelAPI.getConversations === "function") {
            store.conversations = await window.AIModelAPI.getConversations();
          }
          if (typeof window.AIModelAPI.getProfiles === "function") {
            store.profiles = await window.AIModelAPI.getProfiles();
          }
          if (typeof window.AIModelAPI.getSecretKeys === "function") {
            store.secretKeys = await window.AIModelAPI.getSecretKeys();
          }
          if (typeof window.AIModelAPI.getInvoices === "function") {
            store.invoices = await window.AIModelAPI.getInvoices();
          }
          if (typeof window.AIModelAPI.getAdminOverview === "function") {
            store.adminOverview = await window.AIModelAPI.getAdminOverview();
          }
          await loadTrainingData();
          syncNotificationsFromState();
        } catch (err) {
          store.error = err.message;
          if (err.message.includes("401") || err.message.toLowerCase().includes("token")) {
            logout(true);
            store.authError = "Your session expired. Please sign in again.";
          }
        }
      };

      const submitAuth = async () => {
        store.error = "";
        store.authError = "";
        const username = authForm.value.username.trim();
        const password = authForm.value.password;

        if (store.authMode === "register") {
          store.authError = "Public member sign-up is on http://127.0.0.1:5173. Backend :8000/control/ requires an Admin / staff account.";
          return;
        }
        if (!username) {
          store.authError = "Username is required.";
          return;
        }

        store.authBusy = true;
        try {
          await window.AIModelAPI.login(username, password);
          const profile = await window.AIModelAPI.getProfile();
          if (!profile || (!profile.is_staff && !profile.is_superuser)) {
            window.AIModelAPI.clearTokens();
            store.authError = "Admin / staff privileges required on http://localhost:8000/. Members use http://127.0.0.1:5173.";
            return;
          }
          const targetPath = window.AIModelPortalRoute.sanitizeNextPath(store.postAuthPath);
          const targetRoute = window.AIModelPortalRoute.parsePath(targetPath, null);
          applyingPopState = true;
          store.activeSection = targetRoute.section;
          store.activeTask = targetRoute.task;
          store.settingsTab = targetRoute.settingsTab;
          store.adminTab = targetRoute.adminTab || "mfs";
          store.authenticated = true;
          store.showAuthModal = false;
          store.postAuthPath = "/control/";
          store.notice = `Signed in as Admin @${username}.`;
          authForm.value.password = "";
          authForm.value.confirmPassword = "";
          window.history.pushState(
            {
              section: store.activeSection,
              task: store.activeTask,
              settingsTab: store.settingsTab,
              adminTab: store.adminTab,
            },
            "",
            targetPath
          );
          syncDocumentTitle();
          nextTick(() => {
            applyingPopState = false;
          });
          await Promise.all([loadPublicData(), loadDashboard()]);
        } catch (err) {
          store.authError = err.message;
        } finally {
          store.authBusy = false;
        }
      };

      const logout = (preserveError = false) => {
        window.AIModelAPI.clearTokens();
        applyingPopState = true;
        store.authenticated = false;
        store.user = null;
        store.profiles = [];
        store.secretKeys = [];
        store.revealedSecretKey = "";
        store.quota = null;
        store.subscription = null;
        store.plans = [];
        store.health = null;
        store.transactions = [];
        store.invoices = [];
        store.verification = null;
        store.adminOverview = null;
        store.adminBusy = false;
        store.notifications = [];
        store.showNotifications = false;
        store.agents = [];
        store.conversations = [];
        store.activeConversation = null;
        store.trainingStatus = null;
        store.trainingResult = null;
        store.outputs = [];
        store.authMode = "login";
        store.postAuthPath = "/control/";
        store.activeSection = "overview";
        store.adminTab = "mfs";
        if (preserveError !== true) {
          store.error = "";
          store.authError = "";
        }
        window.history.pushState({ auth: true }, "", "/");
        syncDocumentTitle();
        nextTick(() => {
          applyingPopState = false;
        });
      };

      const selectConversation = async (id) => {
        try {
          const detail = await window.AIModelAPI.getConversation(id);
          store.activeConversation = detail;
          store.activeTask = detail.task || "chat";
        } catch (err) {
          store.error = err.message;
        }
      };

      const startNewConversation = async () => {
        if (!store.authenticated) {
          store.showAuthModal = true;
          return;
        }
        store.outputs = [];
        try {
          if (typeof window.AIModelAPI.createConversation === "function") {
            const created = await window.AIModelAPI.createConversation({
              title: "New Conversation",
              task: store.activeTask,
              tier: store.activeTier,
            });
            store.activeConversation = created;
            store.conversations = [created, ...store.conversations.filter((c) => c.id !== created.id)];
          } else {
            store.activeConversation = null;
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const deleteConversation = async (id) => {
        try {
          await window.AIModelAPI.deleteConversation(id);
          store.conversations = store.conversations.filter((c) => c.id !== id);
          if (store.activeConversation?.id === id) {
            store.activeConversation = null;
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const loadTrainingData = async () => {
        try {
          if (typeof window.AIModelAPI.getTrainingStatus === "function") {
            store.trainingStatus = await window.AIModelAPI.getTrainingStatus();
          }
          if (typeof window.AIModelAPI.getTrainingSamples === "function") {
            store.trainingSamples = await window.AIModelAPI.getTrainingSamples();
          }
          if (typeof window.AIModelAPI.getTrainingHistory === "function") {
            store.trainingHistory = await window.AIModelAPI.getTrainingHistory(30);
          }
          if (typeof window.AIModelAPI.getTrainingCheckpoints === "function") {
            store.trainingCheckpoints = await window.AIModelAPI.getTrainingCheckpoints();
          }
        } catch (err) {
          console.warn("Training telemetry load error:", err);
        }
      };

      const runTrainingAction = async (apiCall, buildNotice) => {
        if (!store.authenticated) {
          store.showAuthModal = true;
          return;
        }
        store.trainingBusy = true;
        store.error = "";
        try {
          const result = await apiCall();
          const tierResults = result.tier_results || [];
          store.trainingResult = tierResults.length ? tierResults[tierResults.length - 1] : result;
          await loadTrainingData();
          store.notice = buildNotice(result);
        } catch (err) {
          store.error = err.message;
        } finally {
          store.trainingBusy = false;
        }
      };

      const trainEngine = () =>
        runTrainingAction(
          () =>
            window.AIModelAPI.trainEngine({
              tier: store.activeTier,
              backend: store.activeBackend,
              epochs: Number(store.trainingConfig?.epochs || 8),
              learning_rate: Number(store.trainingConfig?.learningRate || 0.012),
              include_builtin_dataset: store.trainingConfig?.includeBuiltin !== false,
              include_recent_conversations: store.trainingConfig?.includeConversations !== false,
              save_checkpoint: true,
            }),
          (result) =>
            `Trained ${(result.backends_trained || []).length} backend(s) on ${result.dataset_size} samples.`,
        );

      const trainAll = () =>
        runTrainingAction(
          () =>
            window.AIModelAPI.trainAll({
              backend: store.activeBackend || "hybrid",
              epochs: Number(store.trainingConfig?.epochs || 8),
              learning_rate: Number(store.trainingConfig?.learningRate || 0.012),
              include_builtin_dataset: store.trainingConfig?.includeBuiltin !== false,
              include_recent_conversations: store.trainingConfig?.includeConversations !== false,
              save_checkpoint: true,
            }),
          (result) =>
            `Trained all tiers (${(result.tier_results || []).length} tiers, ${result.dataset_size} samples).`,
        );

      const resetTrainingEngine = () =>
        runTrainingAction(
          () => window.AIModelAPI.resetTraining(),
          (res) => `Cleared ${res.removed_files || 0} checkpoint file(s); ${res.dataset_size || 0} built-in samples active.`,
        );

      const createTrainingSample = async (payload) => {
        if (!store.authenticated) {
          store.showAuthModal = true;
          return;
        }
        store.trainingBusy = true;
        store.error = "";
        try {
          await window.AIModelAPI.createTrainingSample(payload);
          await loadTrainingData();
          store.notice = "Saved training sample to tblinc Cloud Storage.";
        } catch (err) {
          store.error = err.message;
        } finally {
          store.trainingBusy = false;
        }
      };

      const bulkUploadTrainingJson = async (file) => {
        if (!file || !store.authenticated) return;
        store.trainingBusy = true;
        store.error = "";
        try {
          const text = await file.text();
          let records = [];
          if (file.name.toLowerCase().endsWith(".jsonl")) {
            records = text.split(/\r?\n/).filter((l) => l.trim()).map((l) => JSON.parse(l));
          } else if (file.name.toLowerCase().endsWith(".txt")) {
            const lines = text.split(/\r?\n/);
            let curQ = "", curA = [];
            let buf = [];
            for (const line of lines) {
              const s = line.trim();
              if (!s) {
                if (curQ && curA.length) {
                  records.push({ prompt: curQ.slice(0, 500), response: curA.join("\n").slice(0, 4000), intent: "text_corpus", task: "chat" });
                  curQ = ""; curA = [];
                } else if (buf.length) {
                  const para = buf.join(" ").trim();
                  buf = [];
                  if (para.length >= 15) {
                    for (const delim of ["?", "\n", ".", ":"]) {
                      if (para.includes(delim)) {
                        const idx = para.indexOf(delim);
                        const p = para.slice(0, idx + (delim === "?" || delim === "." ? 1 : 0)).trim();
                        const r = para.slice(idx + 1).trim();
                        if (p.length >= 5 && r.length >= 10) {
                          records.push({ prompt: p.slice(0, 500), response: r.slice(0, 4000), intent: "text_corpus", task: "chat" });
                          break;
                        }
                      }
                    }
                  }
                }
                continue;
              }
              if (/^(?:q(?:uestion)?|user|human|prompt)\s*:\s*/i.test(s)) {
                if (curQ && curA.length) {
                  records.push({ prompt: curQ.slice(0, 500), response: curA.join("\n").slice(0, 4000), intent: "text_corpus", task: "chat" });
                }
                curQ = s.replace(/^(?:q(?:uestion)?|user|human|prompt)\s*:\s*/i, "");
                curA = [];
              } else if (/^(?:a(?:nswer)?|assistant|bot|response)\s*:\s*/i.test(s)) {
                curA.push(s.replace(/^(?:a(?:nswer)?|assistant|bot|response)\s*:\s*/i, ""));
              } else if (curA.length > 0) {
                curA.push(s);
              } else {
                buf.push(s);
              }
            }
            if (curQ && curA.length) {
              records.push({ prompt: curQ.slice(0, 500), response: curA.join("\n").slice(0, 4000), intent: "text_corpus", task: "chat" });
            }
          } else {
            const parsed = JSON.parse(text);
            records = Array.isArray(parsed) ? parsed : (parsed.samples || parsed.data || []);
          }
          if (!Array.isArray(records) || !records.length) {
            throw new Error("No valid training sample objects found in file.");
          }
          const res = await window.AIModelAPI.createTrainingSample({ samples: records });
          await loadTrainingData();
          store.notice = `Imported ${res.created || records.length} sample(s) from ${file.name} into tblinc Cloud Storage.`;
        } catch (err) {
          store.error = err.message;
        } finally {
          store.trainingBusy = false;
        }
      };

      const deleteTrainingSample = async (id) => {
        store.trainingBusy = true;
        store.error = "";
        try {
          await window.AIModelAPI.deleteTrainingSample(id);
          await loadTrainingData();
          store.notice = "Deleted training sample.";
        } catch (err) {
          store.error = err.message;
        } finally {
          store.trainingBusy = false;
        }
      };

      const evaluateTrainingPrompt = async (prompt) => {
        store.trainingBusy = true;
        store.error = "";
        try {
          store.trainingEvalResult = await window.AIModelAPI.evaluateTraining({
            prompt,
            tier: store.activeTier,
            backend: store.activeBackend,
            task: store.activeTask,
          });
        } catch (err) {
          store.error = err.message;
        } finally {
          store.trainingBusy = false;
        }
      };

      const changePassword = async (current_password, new_password) => {
        try {
          if (typeof window.AIModelAPI.changePassword === "function") {
            await window.AIModelAPI.changePassword({ current_password, new_password });
            store.notice = "Password updated successfully.";
            return true;
          }
          return false;
        } catch (err) {
          store.error = err.message;
          return false;
        }
      };

      const attachStudioMedia = async (file) => {
        if (!file) return;
        store.error = "";
        try {
          const readAsDataUrl = (f) =>
            new Promise((resolve, reject) => {
              const r = new FileReader();
              r.onload = () => resolve(String(r.result || ""));
              r.onerror = () => reject(new Error("Failed to read file."));
              r.readAsDataURL(f);
            });
          const drawCanvas = (src, sw, sh, maxEdge) => {
            const scale = Math.min(1, maxEdge / Math.max(1, sw, sh));
            const w = Math.max(16, Math.round(sw * scale));
            const h = Math.max(16, Math.round(sh * scale));
            const c = document.createElement("canvas");
            c.width = w;
            c.height = h;
            c.getContext("2d").drawImage(src, 0, 0, w, h);
            return { width: w, height: h, dataUrl: c.toDataURL("image/png") };
          };
          if (file.type.startsWith("video/")) {
            const url = URL.createObjectURL(file);
            try {
              const v = document.createElement("video");
              v.muted = true;
              v.playsInline = true;
              v.src = url;
              await new Promise((res, rej) => {
                v.onloadedmetadata = res;
                v.onerror = () => rej(new Error("Unsupported video format."));
              });
              const dur = Number.isFinite(v.duration) && v.duration > 0 ? v.duration : 1.0;
              const frames = [];
              let fw = v.videoWidth || 320;
              let fh = v.videoHeight || 240;
              for (const ratio of dur > 0.4 ? [0.15, 0.5, 0.85] : [0]) {
                await new Promise((r) => {
                  v.addEventListener("seeked", r, { once: true });
                  v.currentTime = Math.max(0, dur * ratio);
                });
                const snap = drawCanvas(v, fw, fh, 320);
                fw = snap.width;
                fh = snap.height;
                frames.push(snap.dataUrl);
              }
              store.studioAttachment = {
                kind: "video",
                filename: file.name,
                mimeType: file.type || "video/mp4",
                width: fw,
                height: fh,
                previewDataUrl: frames[0],
                framesBase64: frames,
              };
            } finally {
              URL.revokeObjectURL(url);
            }
          } else if (file.type.startsWith("image/")) {
            const rawUrl = await readAsDataUrl(file);
            const img = await new Promise((res, rej) => {
              const i = new Image();
              i.onload = () => res(i);
              i.onerror = () => rej(new Error("Unsupported image format."));
              i.src = rawUrl;
            });
            const snap = drawCanvas(img, img.naturalWidth || 256, img.naturalHeight || 256, 512);
            store.studioAttachment = {
              kind: "image",
              filename: file.name,
              mimeType: file.type === "image/gif" ? "image/gif" : "image/png",
              width: snap.width,
              height: snap.height,
              previewDataUrl: file.type === "image/gif" && file.size <= 2 * 1024 * 1024 ? rawUrl : snap.dataUrl,
              imageBase64: file.type === "image/gif" && file.size <= 2 * 1024 * 1024 ? rawUrl : snap.dataUrl,
            };
          } else {
            store.error = "Select an image or video file.";
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const runTask = async () => {
        if (!store.authenticated) {
          store.showAuthModal = true;
          return;
        }
        const att = store.studioAttachment;
        const currentPrompt = store.prompt.trim() || (
          att
            ? (att.kind === "video" || store.activeTask === "video"
              ? "Generate animated video from uploaded media"
              : "Generate styled artwork from uploaded media")
            : ""
        );
        if (!currentPrompt) return;
        store.loading = true;
        store.error = "";
        try {
          const payload = {
            prompt: currentPrompt,
            tier: store.activeTier,
            backend: store.activeBackend,
            language: store.activeTask === "code" ? store.language : undefined,
            duration_seconds: store.activeTask === "video" ? store.videoDurationSeconds : undefined,
            system_prompt: store.systemPrompt.trim() || undefined,
            conversation_id: store.activeConversation?.id || null,
            ...(att
              ? {
                  metadata: {
                    media_kind: att.kind,
                    media_filename: att.filename,
                    reference_mime_type: att.mimeType,
                    ...(att.imageBase64 ? { reference_image_base64: att.imageBase64 } : {}),
                    ...(att.framesBase64 ? { reference_frames_base64: att.framesBase64 } : {}),
                  },
                }
              : {}),
          };
          const res = await window.AIModelAPI.generate(store.activeTask, payload);
          store.outputs.unshift(res);
          store.prompt = "";
          store.studioAttachment = null;
          if (res.quota) store.quota = res.quota;
          if (res.conversation_id) {
            store.activeConversation = await window.AIModelAPI.getConversation(res.conversation_id);
          }
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.loading = false;
        }
      };

      const createAgent = async (payload) => {
        try {
          if (typeof window.AIModelAPI.createAgent === "function") {
            await window.AIModelAPI.createAgent(payload);
            store.notice = `Agent '${payload.name}' created.`;
            await loadDashboard();
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const runAgent = async (agentId) => {
        if (!store.authenticated) {
          store.showAuthModal = true;
          return;
        }
        store.loading = true;
        store.error = "";
        try {
          const res = await window.AIModelAPI.executeAgent({
            agent_id: agentId,
            prompt: store.prompt,
            tier: store.activeTier,
            task: store.activeTask,
            backend: store.activeBackend,
          });
          if (res.result) store.outputs.unshift(res.result);
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.loading = false;
        }
      };

      const topupValid = computed(() => {
        const raw = String(topupAmount.value ?? "").trim();
        if (!/^\d+$/.test(raw)) return false;
        const val = Number(raw);
        return val >= 10 && val <= 100000;
      });

      const topupValidationMsg = computed(() => {
        const raw = String(topupAmount.value ?? "").trim();
        if (!/^\d+$/.test(raw)) return "Enter a whole number of credits (10 to 100,000).";
        const val = Number(raw);
        if (val < 10) return "Minimum checkout purchase is 10 credits ($0.10).";
        if (val > 100000) return "Maximum single checkout is 100,000 credits ($1,000.00).";
        return "";
      });

      const selectedCheckoutPlan = computed(() => {
        const list = store.plans || [];
        return list.find((p) => p.slug === store.checkoutPlanSlug) || null;
      });

      const projectedCreditBalance = computed(
        () => (store.quota?.remaining_credits || 0) + (topupValid.value ? Number(topupAmount.value) : 0)
      );

      const projectedPlanBalance = computed(() => {
        const current = store.quota?.remaining_credits || 0;
        const plan = selectedCheckoutPlan.value;
        if (!plan) return current;
        const grant = Number(plan.monthly_price_usd) === 0 ? 0 : Number(plan.monthly_credits || 0);
        return current + grant;
      });

      const BDT_PER_USD = 120;
      const mfsMethods = [
        { id: "bkash", label: "bKash", hint: "bKash Merchant / Send Money" },
        { id: "nagad", label: "Nagad", hint: "Nagad Send Money" },
        { id: "rocket", label: "Rocket", hint: "DBBL Rocket Wallet" },
        { id: "upay", label: "Upay", hint: "Upay Digital Wallet" },
      ];

      const usdToBdt = (amountUsd) => window.AIModelBilling.usdToBdt(amountUsd);

      const resolvePlanBdt = (plan) => {
        if (plan && plan.monthly_price_bdt !== undefined && plan.monthly_price_bdt !== null) {
          const parsed = Number(plan.monthly_price_bdt);
          if (Number.isFinite(parsed)) return parsed;
        }
        return usdToBdt(plan ? plan.monthly_price_usd : 0);
      };

      const formatBdt = (amountBdt) => window.AIModelBilling.formatBdt(amountBdt);

      const formatCreditsBdtUsd = (credits, opts) =>
        window.AIModelBilling.formatCreditsBdtUsd(credits, opts);

      const formatPaymentMethodLabel = (method) => {
        const clean = String(method || "").trim().toLowerCase();
        const found = mfsMethods.find((m) => m.id === clean);
        return found ? found.label : (clean ? clean.toUpperCase() : "—");
      };

      const selectedMfsMeta = computed(
        () => mfsMethods.find((m) => m.id === store.checkoutMethod) || mfsMethods[0]
      );

      const tnxidValid = computed(() =>
        /^[A-Z0-9_-]{6,64}$/.test(String(store.checkoutTnxid || "").trim().toUpperCase())
      );

      const openCheckout = (mode = "credits", planSlug = "") => {
        store.checkoutMode = mode === "plans" ? "plans" : "credits";
        store.checkoutError = "";
        store.checkoutReceipt = null;
        store.checkoutBusy = false;
        store.checkoutTnxid = "";
        topupAmount.value = 500;
        const plansList = store.plans || [];
        if (planSlug && plansList.some((p) => p.slug === planSlug)) {
          store.checkoutPlanSlug = planSlug;
        } else {
          const currentSlug = store.subscription?.plan?.slug;
          const nextPlan = plansList.find((p) => p.slug !== currentSlug) || plansList[0];
          store.checkoutPlanSlug = nextPlan ? nextPlan.slug : "";
        }
        store.showTopupModal = true;
        refreshIcons();
      };

      const closeCheckout = () => {
        if (store.checkoutBusy) return;
        store.showTopupModal = false;
        store.checkoutError = "";
        store.checkoutReceipt = null;
        store.checkoutTnxid = "";
      };

      const subscribePlan = async (slug) => {
        const targetSlug = slug || store.checkoutPlanSlug;
        if (!targetSlug || store.checkoutBusy) return;
        const targetPlan = (store.plans || []).find((p) => p.slug === targetSlug) || null;
        const isFree = targetPlan ? Number(targetPlan.monthly_price_usd) === 0 : false;
        const cleanTnxid = String(store.checkoutTnxid || "").trim().toUpperCase();
        if (store.showTopupModal && !isFree && !tnxidValid.value) {
          store.checkoutError = `Enter a valid ${selectedMfsMeta.value.label} TrxID (min 6 alphanumeric characters).`;
          return;
        }
        store.error = "";
        store.checkoutError = "";
        store.checkoutBusy = true;
        try {
          const bdtDue = targetPlan ? resolvePlanBdt(targetPlan) : 0;
          const paymentPayload =
            store.showTopupModal && !isFree
              ? {
                  currency: "BDT",
                  amount_bdt: bdtDue.toFixed(2),
                  payment_method: store.checkoutMethod,
                  tnxid: cleanTnxid,
                }
              : undefined;
          const res = await window.AIModelAPI.subscribePlan(targetSlug, paymentPayload);
          if (res.subscription) store.subscription = res.subscription;
          if (res.quota) store.quota = res.quota;
          if (res.invoice) store.invoices = [res.invoice, ...(store.invoices || [])];
          const planName = res.subscription?.plan?.name || targetSlug;
          const invNum = res.invoice?.invoice_number || `INV-${Date.now()}`;
          const newBal = res.quota?.remaining_credits ?? store.quota?.remaining_credits ?? 0;
          store.notice = `Subscribed to ${planName} (${invNum}).`;
          pushNotification(
            `sub-${invNum}`,
            "Plan Activated",
            `Switched to ${planName} · Balance: ${formatCreditsBdtUsd(newBal)}.`,
            false
          );
          if (store.showTopupModal) {
            store.checkoutReceipt = {
              kind: "plan",
              reference: invNum,
              title: `${planName} Monthly Plan`,
              amountUsd: String(res.invoice?.amount_usd ?? res.subscription?.plan?.monthly_price_usd ?? "0.00"),
              amountBdt: String(res.invoice?.amount_bdt ?? bdtDue.toFixed(2)),
              paymentMethod: res.invoice?.payment_method || "",
              tnxid: res.invoice?.tnxid || "",
              creditsAdded: Number(res.invoice?.credits_granted ?? 0),
              balanceAfter: Number(newBal),
              dailyLimit: res.subscription?.plan?.daily_request_limit,
              verified: true,
            };
          }
          store.checkoutTnxid = "";
          await loadDashboard();
        } catch (err) {
          if (store.showTopupModal) {
            store.checkoutError = err.message;
          } else {
            store.error = err.message;
          }
        } finally {
          store.checkoutBusy = false;
        }
      };

      const submitTopup = async () => {
        if (!topupValid.value || !tnxidValid.value || store.checkoutBusy) return;
        const credits = Number(topupAmount.value);
        const expectedUsd = (credits * 0.01).toFixed(2);
        const expectedBdt = usdToBdt(expectedUsd).toFixed(2);
        const cleanTnxid = String(store.checkoutTnxid || "").trim().toUpperCase();
        store.error = "";
        store.checkoutError = "";
        store.checkoutBusy = true;
        try {
          const res = await window.AIModelAPI.topupCredits(credits, {
            currency: "BDT",
            amount_bdt: expectedBdt,
            payment_method: store.checkoutMethod,
            tnxid: cleanTnxid,
          });
          if (res.quota) store.quota = res.quota;
          if (res.transaction) store.transactions = [res.transaction, ...(store.transactions || [])];
          const newBal = res.quota?.remaining_credits ?? res.remaining_credits ?? store.quota?.remaining_credits ?? 0;
          const refId = res.transaction?.reference_id || `TX-${Date.now()}`;
          store.notice = `Added ${formatCreditsBdtUsd(credits)} (${formatPaymentMethodLabel(store.checkoutMethod)} ${cleanTnxid}).`;
          pushNotification(
            `topup-${refId}`,
            "Checkout Completed",
            `Added ${formatCreditsBdtUsd(credits, { compact: true })} · Balance: ${formatCreditsBdtUsd(newBal)}.`,
            false
          );
          store.checkoutReceipt = {
            kind: "credits",
            reference: refId,
            title: `${credits.toLocaleString()} AI Credits Pack`,
            amountUsd: String(res.transaction?.amount_usd ?? expectedUsd),
            amountBdt: String(res.transaction?.amount_bdt ?? expectedBdt),
            paymentMethod: res.transaction?.payment_method || store.checkoutMethod,
            tnxid: res.transaction?.tnxid || cleanTnxid,
            creditsAdded: credits,
            balanceAfter: Number(newBal),
            verified: Boolean(res.transaction?.metadata?.receipt_signature),
          };
          store.checkoutTnxid = "";
          await loadDashboard();
        } catch (err) {
          store.checkoutError = err.message;
        } finally {
          store.checkoutBusy = false;
        }
      };

      const loadAdminOverview = async () => {
        if (!store.authenticated || !store.user || (!store.user.is_staff && !store.user.is_superuser)) return;
        store.adminBusy = true;
        try {
          if (typeof window.AIModelAPI.getAdminOverview === "function") {
            store.adminOverview = await window.AIModelAPI.getAdminOverview();
          }
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const approveMfsRequest = async (id, note = "") => {
        if (!id || store.adminBusy) return;
        store.error = "";
        store.adminBusy = true;
        try {
          const res = await window.AIModelAPI.approveMfsRequest(id, note);
          const req = res.request;
          store.notice = req
            ? `Approved ${formatPaymentMethodLabel(req.payment_method)} ${req.tnxid} for @${req.username}.`
            : "Approved MFS payment request.";
          pushNotification(
            `mfs-app-${id}`,
            "MFS Payment Approved",
            req ? `@${req.username} · ৳${req.amount_bdt} (${req.tnxid}) credited.` : "Member payment approved.",
            false
          );
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const rejectMfsRequest = async (id, note = "") => {
        if (!id || store.adminBusy) return;
        store.error = "";
        store.adminBusy = true;
        try {
          const res = await window.AIModelAPI.rejectMfsRequest(id, note);
          const req = res.request;
          store.notice = req
            ? `Rejected ${formatPaymentMethodLabel(req.payment_method)} ${req.tnxid} for @${req.username}.`
            : "Rejected MFS payment request.";
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const adminGrantCredits = async (userId, credits, description = "") => {
        if (!userId || !(Number(credits) >= 1) || store.adminBusy) return;
        store.error = "";
        store.adminBusy = true;
        try {
          const res = await window.AIModelAPI.adminGrantCredits({
            user_id: Number(userId),
            credits: Number(credits),
            description,
          });
          store.notice = `Granted ${formatCreditsBdtUsd(credits)} (new balance: ${formatCreditsBdtUsd(res.quota?.remaining_credits)}).`;
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const adminClearBalance = async (userId, username = "", description = "") => {
        if (!userId || store.adminBusy) return;
        store.error = "";
        store.adminBusy = true;
        try {
          const res = await window.AIModelAPI.adminClearBalance({
            user_id: Number(userId),
            description,
          });
          const label = username ? `@${username}` : `user #${userId}`;
          store.notice = `Cleared ${formatCreditsBdtUsd(res.cleared_credits || 0)} from ${label} (balance: ${formatCreditsBdtUsd(res.quota?.remaining_credits ?? 0)}).`;
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const adminSwitchUserPlan = async (userId, planSlug) => {
        if (!userId || !planSlug || store.adminBusy) return;
        store.error = "";
        store.adminBusy = true;
        try {
          const res = await window.AIModelAPI.adminSwitchPlan({
            user_id: Number(userId),
            plan_slug: planSlug,
          });
          store.notice = `Switched member plan to ${res.subscription?.plan?.name || planSlug}.`;
          await loadDashboard();
        } catch (err) {
          store.error = err.message;
        } finally {
          store.adminBusy = false;
        }
      };

      const updateProfile = async (payloadOrEmail) => {
        try {
          if (typeof window.AIModelAPI.updateProfile === "function") {
            const payload = typeof payloadOrEmail === "string" ? { email: payloadOrEmail } : payloadOrEmail;
            const updated = await window.AIModelAPI.updateProfile(payload);
            store.user = Object.assign({}, store.user || {}, updated);
            if (updated.default_tier) {
              store.activeTier = updated.default_tier;
              localStorage.setItem("ai_model_backend_active_tier", updated.default_tier);
            }
            if (updated.default_task) store.activeTask = updated.default_task;
            store.notice = `Profile updated (@${updated.username}).`;
            await loadDashboard();
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const verifyAccount = async (reconcile = true) => {
        try {
          if (typeof window.AIModelAPI.verifyAccount === "function") {
            const report = await window.AIModelAPI.verifyAccount(reconcile);
            store.verification = report;
            store.notice = report.verified
              ? `Account verified (@${report.profile?.username}: ${formatCreditsBdtUsd(report.balance?.remaining_credits)} balanced).`
              : `Verification checked (${(report.issues || []).join(", ") || "see details"}).`;
            await loadDashboard();
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const createSecretKey = async (name) => {
        try {
          if (typeof window.AIModelAPI.createSecretKey === "function") {
            const created = await window.AIModelAPI.createSecretKey(name);
            store.revealedSecretKey = created.secret_key || "";
            store.secretKeys.unshift(created);
            store.notice = `Created API key '${created.name}'. Copy it before leaving.`;
            pushNotification(`key-${created.id}`, "API Key Created", `Generated '${created.name}'.`, false);
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const toggleSecretKey = async (id, nextActive) => {
        try {
          if (typeof window.AIModelAPI.toggleSecretKey === "function") {
            const updated = await window.AIModelAPI.toggleSecretKey(id, nextActive);
            store.secretKeys = store.secretKeys.map((k) => (k.id === id ? updated : k));
            store.notice = `API key ${nextActive ? "enabled" : "paused"}.`;
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const revokeSecretKey = async (id) => {
        try {
          if (typeof window.AIModelAPI.revokeSecretKey === "function") {
            await window.AIModelAPI.revokeSecretKey(id);
            store.secretKeys = store.secretKeys.filter((k) => k.id !== id);
            store.notice = "Secret key revoked.";
          }
        } catch (err) {
          store.error = err.message;
        }
      };

      const unreadNotificationsCount = computed(() =>
        (store.notifications || []).filter((n) => !n.read).length
      );

      const pushNotification = (id, title, message, read = false) => {
        const key = String(id);
        if ((store.notifications || []).some((n) => n.id === key)) return;
        store.notifications.unshift({
          id: key,
          title,
          message,
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          read,
        });
        if (store.notifications.length > 20) {
          store.notifications = store.notifications.slice(0, 20);
        }
      };

      const syncNotificationsFromState = () => {
        for (const tx of (store.transactions || []).slice(0, 5)) {
          pushNotification(
            `tx-${tx.reference_id}`,
            `${formatCreditsBdtUsd(tx.credits_delta, { signed: true, compact: true })} · ${tx.tx_type}`,
            tx.description || "Ledger transaction",
            true
          );
        }
        if (store.verification?.issues?.length) {
          pushNotification(
            `verify-${store.verification.issues.join("-")}`,
            "Account Verification",
            `Issues: ${store.verification.issues.join(", ")}`,
            false
          );
        }
        if (store.quota && store.quota.remaining_credits <= 25) {
          pushNotification(
            `low-bal-${store.quota.remaining_credits}`,
            "Low Balance",
            `Only ${formatCreditsBdtUsd(store.quota.remaining_credits)} left. Use Deposit to top up.`,
            false
          );
        }
      };

      const toggleNotifications = () => {
        store.showNotifications = !store.showNotifications;
      };

      const markAllNotificationsRead = () => {
        store.notifications = (store.notifications || []).map((n) => ({ ...n, read: true }));
      };

      const clearNotifications = () => {
        store.notifications = [];
        store.showNotifications = false;
      };

      let applyingPopState = false;

      const syncDocumentTitle = () => {
        if (!store.authenticated) {
          document.title = store.authMode === "register" ? "Sign Up · tblinc AI" : "Login · tblinc AI";
          return;
        }
        document.title = `${sectionTitle.value} · tblinc AI`;
      };

      const applyParsedRoute = (parsed) => {
        store.activeSection = parsed.section;
        store.activeTask = parsed.task;
        store.settingsTab = parsed.settingsTab;
        store.adminTab = parsed.adminTab || "mfs";
      };

      const currentHistoryState = () => ({
        section: store.activeSection,
        task: store.activeTask,
        settingsTab: store.settingsTab,
        adminTab: store.adminTab,
      });

      const applyRouteFromLocation = () => {
        if (!window.AIModelPortalRoute) return;
        applyingPopState = true;
        if (!store.authenticated) {
          if (!window.AIModelPortalRoute.isAuthPath(window.location.pathname)) {
            store.postAuthPath = window.AIModelPortalRoute.sanitizeNextPath(window.location.pathname);
            window.history.replaceState({ auth: true }, "", "/");
          }
          syncDocumentTitle();
          nextTick(() => {
            applyingPopState = false;
          });
          return;
        }
        if (window.AIModelPortalRoute.isAuthPath(window.location.pathname)) {
          const targetPath = window.AIModelPortalRoute.sanitizeNextPath(store.postAuthPath);
          const parsedTarget = window.AIModelPortalRoute.parsePath(targetPath, null);
          applyParsedRoute(parsedTarget);
          window.history.replaceState(currentHistoryState(), "", targetPath);
          syncDocumentTitle();
          nextTick(() => {
            applyingPopState = false;
          });
          return;
        }
        const parsed = window.AIModelPortalRoute.parsePath(window.location.pathname, null);
        applyParsedRoute(parsed);
        syncDocumentTitle();
        nextTick(() => {
          applyingPopState = false;
        });
      };

      watch(
        () => [
          store.authenticated,
          store.authMode,
          store.activeSection,
          store.activeTask,
          store.settingsTab,
          store.adminTab,
        ],
        ([authenticated, _mode, section, task, settingsTab, adminTab]) => {
          syncDocumentTitle();
          if (!authenticated || applyingPopState || !window.AIModelPortalRoute) return;
          const nextPath = window.AIModelPortalRoute.buildPath(
            section,
            task,
            settingsTab,
            window.location.pathname,
            adminTab
          );
          if (window.location.pathname !== nextPath) {
            window.history.pushState(
              { section, task, settingsTab, adminTab },
              "",
              nextPath
            );
          }
        }
      );

      const handleDocumentClick = () => {
        store.modelDropdownOpen = false;
        store.showNotifications = false;
        store.showUserMenu = false;
        store.showSidebarUserMenu = false;
      };

      onMounted(async () => {
        if (!store.authenticated && !window.AIModelPortalRoute.isAuthPath(window.location.pathname)) {
          store.postAuthPath = window.AIModelPortalRoute.sanitizeNextPath(window.location.pathname);
          window.history.replaceState({ auth: true }, "", "/");
        } else if (store.authenticated && window.AIModelPortalRoute.isAuthPath(window.location.pathname)) {
          const targetPath = window.AIModelPortalRoute.sanitizeNextPath(store.postAuthPath);
          const parsedTarget = window.AIModelPortalRoute.parsePath(targetPath, null);
          applyingPopState = true;
          applyParsedRoute(parsedTarget);
          window.history.replaceState(currentHistoryState(), "", targetPath);
          nextTick(() => {
            applyingPopState = false;
          });
        } else {
          window.history.replaceState(currentHistoryState(), "", window.location.pathname);
        }
        syncDocumentTitle();
        document.addEventListener("click", handleDocumentClick);
        window.addEventListener("popstate", applyRouteFromLocation);
        await loadPublicData();
        await loadDashboard();
        refreshIcons();
        window.AIModelMotion.animateEntrance(".glass-panel");
      });

      onUnmounted(() => {
        document.removeEventListener("click", handleDocumentClick);
        window.removeEventListener("popstate", applyRouteFromLocation);
      });

      onUpdated(refreshIcons);

      return {
        store,
        authForm,
        topupAmount,
        studioModes,
        portalHref,
        navigatePortal,
        sectionTitle,
        toggleTheme,
        toggleSidebar,
        openModelSwitcher,
        activeModelCard,
        selectProjectModel,
        selectStudioTask,
        stepModel,
        onModelTouchStart,
        onModelTouchEnd,
        formatModelMeta,
        openAuth,
        switchAuthMode,
        submitAuth,
        logout,
        selectConversation,
        startNewConversation,
        deleteConversation,
        trainEngine,
        trainAll,
        loadTrainingData,
        resetTrainingEngine,
        createTrainingSample,
        bulkUploadTrainingJson,
        deleteTrainingSample,
        evaluateTrainingPrompt,
        attachStudioMedia,
        runTask,
        createAgent,
        runAgent,
        subscribePlan,
        submitTopup,
        openCheckout,
        closeCheckout,
        topupValid,
        topupValidationMsg,
        selectedCheckoutPlan,
        projectedCreditBalance,
        projectedPlanBalance,
        mfsMethods,
        selectedMfsMeta,
        tnxidValid,
        usdToBdt,
        resolvePlanBdt,
        formatBdt,
        formatCreditsBdtUsd,
        formatPaymentMethodLabel,
        updateProfile,
        verifyAccount,
        createSecretKey,
        toggleSecretKey,
        revokeSecretKey,
        unreadNotificationsCount,
        toggleNotifications,
        markAllNotificationsRead,
        clearNotifications,
        changePassword,
        loadAdminOverview,
        approveMfsRequest,
        rejectMfsRequest,
        adminGrantCredits,
        adminSwitchUserPlan,
      };
    },
  });

  app.mount("#app");
})();

