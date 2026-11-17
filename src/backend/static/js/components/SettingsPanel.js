/**
 * Vue 3 CDN unified Settings panel housing General/Security, Agents, Billing & Quota,
 * Profiles, Transactions, and All views.
 */
window.SettingsPanelComponent = {
  components: {
    BillingQuotaPanel: window.BillingQuotaPanelComponent,
    ProfilePanel: window.ProfilePanelComponent,
  },
  props: [
    "store",
    "onToggleTheme",
    "onToggleSidebar",
    "onUpdateProfile",
    "onChangePassword",
    "onSubscribe",
    "onOpenTopup",
    "onVerifyAccount",
    "onCreateSecretKey",
    "onToggleSecretKey",
    "onRevokeSecretKey",
    "onCreateAgent",
    "onRunAgent",
  ],
  template: `
    <section class="space-y-4">
      <!-- Settings Sub-Navigation Tabs -->
      <div class="glass-panel rounded-xl p-2 flex flex-wrap gap-1.5">
        <button
          v-for="tab in tabs"
          :key="'stab-' + tab.id"
          type="button"
          @click="store.settingsTab = tab.id"
          class="px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
          :class="store.settingsTab === tab.id ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/70'"
        >
          <i :data-lucide="tab.icon" class="w-3.5 h-3.5"></i>
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <!-- General & Security Tab -->
      <div v-if="showTab('general')" class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="glass-panel rounded-xl p-4 space-y-3">
            <h2 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <i data-lucide="settings" class="w-4 h-4 text-indigo-600 dark:text-cyan-400"></i>
              <span>Appearance &amp; Workspace Layout</span>
            </h2>

            <div class="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
              <div>
                <div class="text-xs font-semibold text-slate-900 dark:text-white">Color Theme</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400">
                  Active: {{ store.theme === 'dark' ? 'Dark Mode' : 'Light Mode' }}
                </div>
              </div>
              <button
                type="button"
                @click="onToggleTheme && onToggleTheme()"
                class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5"
              >
                <i :data-lucide="store.theme === 'dark' ? 'sun' : 'moon'" class="w-3.5 h-3.5"></i>
                <span>{{ store.theme === 'dark' ? 'Switch to Light' : 'Switch to Dark' }}</span>
              </button>
            </div>

            <div class="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
              <div>
                <div class="text-xs font-semibold text-slate-900 dark:text-white">Desktop Sidenav</div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400">
                  {{ store.sidebarCollapsed ? 'Collapsed icon bar' : 'Expanded full sidebar' }}
                </div>
              </div>
              <button
                type="button"
                @click="onToggleSidebar && onToggleSidebar()"
                class="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs font-semibold"
              >
                {{ store.sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar' }}
              </button>
            </div>
          </div>

          <form @submit.prevent="saveDefaults" class="glass-panel rounded-xl p-4 space-y-3">
            <div class="flex items-center justify-between">
              <h2 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
                <i data-lucide="sparkles" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
                <span>AI Engine Defaults</span>
              </h2>
              <button type="submit" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold">
                Save Defaults
              </button>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label class="block text-[11px] font-mono text-slate-500 mb-1">Tier</label>
                <select v-model="store.activeTier" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100">
                  <option value="flash">tblinc Flash</option>
                  <option value="pro">tblinc Pro</option>
                  <option value="advance">tblinc Advance</option>
                </select>
              </div>
              <div>
                <label class="block text-[11px] font-mono text-slate-500 mb-1">Mode</label>
                <select v-model="store.activeTask" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100">
                  <option value="chat">AI Chat</option>
                  <option value="images">Create Images</option>
                  <option value="video">Create Videos</option>
                  <option value="code">Create Code</option>
                </select>
              </div>
              <div>
                <label class="block text-[11px] font-mono text-slate-500 mb-1">Cloud Engine</label>
                <select v-model="store.activeBackend" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100">
                  <option value="numpy">tblinc Cloud Core (Fast Compute)</option>
                  <option value="pytorch">tblinc Cloud Flash Engine</option>
                  <option value="tensorflow">tblinc Cloud Pro Engine</option>
                  <option value="keras">tblinc Cloud Advance Engine</option>
                  <option value="hybrid">tblinc Cloud Ensemble (All Engines)</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[11px] font-mono text-slate-500 mb-1">Default System Instruction</label>
              <input v-model="store.systemPrompt" type="text" placeholder="Optional system prompt..." class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
            </div>
          </form>
        </div>

        <form @submit.prevent="submitPassword" class="glass-panel rounded-xl p-4 space-y-3">
          <h2 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
            <i data-lucide="lock" class="w-4 h-4 text-amber-600 dark:text-amber-400"></i>
            <span>Change Password</span>
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <input v-model="pw.current" type="password" required placeholder="Current password" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
            <input v-model="pw.next" type="password" required minlength="8" placeholder="New password (8+ chars)" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
            <input v-model="pw.confirm" type="password" required minlength="8" placeholder="Confirm password" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
          </div>
          <div class="flex justify-end">
            <button type="submit" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold">
              Update Password
            </button>
          </div>
        </form>
      </div>

      <!-- Agents Tab -->
      <div v-if="showTab('agents')" class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <form @submit.prevent="submitAgent" class="glass-panel rounded-xl p-4 space-y-2.5">
            <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <i data-lucide="plus" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
              <span>Create Agent</span>
            </h3>
            <input v-model="agentForm.name" type="text" required placeholder="Agent name (e.g. Vision Shader Agent)" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
            <textarea v-model="agentForm.system_prompt" rows="2" placeholder="System instruction..." class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2.5 text-xs text-slate-900 dark:text-slate-100"></textarea>
            <div class="grid grid-cols-2 gap-2">
              <select v-model="agentForm.default_tier" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100">
                <option value="flash">tblinc Flash</option>
                <option value="pro">tblinc Pro</option>
                <option value="advance">tblinc Advance</option>
              </select>
              <select v-model="agentForm.default_task" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100">
                <option value="chat">AI Chat</option>
                <option value="images">Create Images</option>
                <option value="video">Create Videos</option>
                <option value="code">Create Code</option>
              </select>
            </div>
            <button type="submit" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold">
              Create Agent
            </button>
          </form>

          <div class="glass-panel rounded-xl p-4 space-y-2.5">
            <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <i data-lucide="bot" class="w-4 h-4 text-purple-600 dark:text-purple-400"></i>
              <span>Registered Agents ({{ store.agents.length }})</span>
            </h3>
            <div class="flex gap-2">
              <input v-model="agentRunPrompt" type="text" placeholder="Task prompt to run with an agent..." class="flex-1 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100" />
            </div>
            <div class="space-y-1.5 max-h-52 overflow-y-auto custom-scroll">
              <div v-for="ag in store.agents" :key="'ag-' + ag.id" class="rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 p-2.5 flex items-center justify-between gap-2">
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-900 dark:text-white truncate">{{ ag.name }}</div>
                  <div class="text-[10px] font-mono text-slate-500">{{ ag.default_tier.toUpperCase() }} · {{ ag.default_task }}</div>
                </div>
                <button
                  type="button"
                  :disabled="!agentRunPrompt.trim() || store.loading"
                  @click="runSelectedAgent(ag.id)"
                  class="px-2.5 py-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-[11px] font-semibold disabled:opacity-45 shrink-0"
                >
                  Run
                </button>
              </div>
              <p v-if="!store.agents.length" class="text-xs text-slate-500">No agents yet.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Billing & Quota Tab -->
      <div v-if="showTab('billing')">
        <billing-quota-panel
          :store="store"
          :on-subscribe="onSubscribe"
          :on-open-topup="onOpenTopup"
          :on-update-profile="onUpdateProfile"
          :on-verify-account="onVerifyAccount"
        ></billing-quota-panel>
      </div>

      <!-- API Keys Tab -->
      <div v-if="showTab('keys')" class="glass-panel rounded-xl p-4 space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
              <i data-lucide="key-round" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
              <span>API Keys</span>
            </h3>
            <p class="text-[11px] text-slate-500">Create &amp; manage API keys (<code class="font-mono">sk_tblinc_...</code>) for REST requests.</p>
          </div>
          <form @submit.prevent="submitKey" class="flex items-center gap-2">
            <input v-model="keyLabel" type="text" placeholder="Key label" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1 text-xs text-slate-900 dark:text-slate-100 w-40" />
            <button type="submit" class="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold">
              + Create API Key
            </button>
          </form>
        </div>
        <div v-if="store.revealedSecretKey" class="rounded-lg bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/35 p-2.5 text-xs space-y-1">
          <div class="font-semibold text-emerald-700 dark:text-emerald-300">New API Key (copy now — shown once):</div>
          <div class="font-mono break-all text-slate-900 dark:text-white">{{ store.revealedSecretKey }}</div>
        </div>
        <div class="space-y-1.5">
          <div v-for="k in store.secretKeys" :key="'ak-' + k.id" class="rounded-lg bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 px-3 py-2 flex items-center justify-between gap-2 text-xs">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-slate-900 dark:text-white truncate">{{ k.name }}</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded" :class="k.is_active ? 'bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'bg-slate-200 dark:bg-slate-800 text-slate-600'">
                  {{ k.is_active ? 'Active' : 'Paused' }}
                </span>
              </div>
              <div class="text-[11px] font-mono text-slate-500">{{ k.key_prefix }}••••••••</div>
            </div>
            <div class="flex items-center gap-1.5">
              <button v-if="onToggleSecretKey" type="button" @click="onToggleSecretKey(k.id, !k.is_active)" class="text-[11px] px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold">
                {{ k.is_active ? 'Pause' : 'Enable' }}
              </button>
              <button v-if="onRevokeSecretKey" type="button" @click="onRevokeSecretKey(k.id)" class="text-[11px] px-2 py-0.5 rounded bg-rose-50 dark:bg-rose-500/15 text-rose-600 dark:text-rose-300 font-semibold">
                Revoke
              </button>
            </div>
          </div>
          <p v-if="!(store.secretKeys || []).length" class="text-[11px] text-slate-500">No API keys created yet.</p>
        </div>
      </div>

      <!-- Profiles Tab -->
      <div v-if="showTab('profiles')">
        <profile-panel
          :store="store"
          :on-update-profile="onUpdateProfile"
        ></profile-panel>
      </div>

      <!-- Transactions Tab -->
      <div v-if="showTab('transactions')" class="glass-panel rounded-xl p-4 space-y-3">
        <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-2">
          <i data-lucide="receipt" class="w-4 h-4 text-purple-600 dark:text-purple-400"></i>
          <span>Credit &amp; Billing Transaction Ledger</span>
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th class="py-2 pr-3">Reference</th>
                <th class="py-2 pr-3">Type</th>
                <th class="py-2 pr-3">Method</th>
                <th class="py-2 pr-3">TrxID</th>
                <th class="py-2 pr-3">Description</th>
                <th class="py-2 pr-3">Credits</th>
                <th class="py-2 pr-3">Balance</th>
                <th class="py-2">Amount (BDT)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 dark:divide-slate-800/70">
              <tr v-for="tx in store.transactions" :key="tx.reference_id" class="text-slate-800 dark:text-slate-200">
                <td class="py-2 pr-3 font-mono text-slate-500">{{ tx.reference_id }}</td>
                <td class="py-2 pr-3 font-mono">{{ tx.tx_type }}</td>
                <td class="py-2 pr-3 font-semibold uppercase">{{ tx.payment_method || '—' }}</td>
                <td class="py-2 pr-3 font-mono text-cyan-600 dark:text-cyan-300">{{ tx.tnxid || '—' }}</td>
                <td class="py-2 pr-3">{{ tx.description }}</td>
                <td class="py-2 pr-3 font-mono font-semibold" :class="tx.credits_delta >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-300'">
                  {{ tx.credits_delta >= 0 ? '+' : '' }}{{ tx.credits_delta }}
                </td>
                <td class="py-2 pr-3 font-mono">{{ tx.balance_after }}</td>
                <td class="py-2 font-mono">৳{{ Number(tx.amount_bdt ?? (Number(tx.amount_usd || 0) * 120)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!store.transactions.length" class="text-xs text-slate-500 py-4 text-center">No transactions recorded yet.</p>
        </div>
      </div>
    </section>
  `,
  setup(props) {
    const { reactive, ref } = Vue;
    const tabs = [
      { id: "general", label: "General", icon: "settings" },
      { id: "keys", label: "API Keys", icon: "key-round" },
      { id: "agents", label: "Agents", icon: "bot" },
      { id: "billing", label: "Billing & Quota", icon: "credit-card" },
      { id: "profiles", label: "Profiles", icon: "user-check" },
      { id: "transactions", label: "Transactions", icon: "receipt" },
      { id: "all", label: "All", icon: "layout-grid" },
    ];
    const keyLabel = ref("Default API Key");
    const pw = reactive({ current: "", next: "", confirm: "" });
    const agentForm = reactive({
      name: "",
      system_prompt: "You are a specialized tblinc AI engineering agent.",
      default_tier: props.store.activeTier || "flash",
      default_task: "chat",
    });
    const agentRunPrompt = ref("");

    const showTab = (tabId) => props.store.settingsTab === tabId || props.store.settingsTab === "all";

    const saveDefaults = () => {
      if (props.onUpdateProfile) {
        props.onUpdateProfile({
          default_tier: props.store.activeTier,
          default_task: props.store.activeTask,
          default_system_prompt: props.store.systemPrompt || "",
        });
      }
    };

    const submitPassword = async () => {
      if (pw.next !== pw.confirm) {
        props.store.error = "Passwords do not match.";
        return;
      }
      if (props.onChangePassword) {
        const ok = await props.onChangePassword(pw.current, pw.next);
        if (ok) {
          pw.current = "";
          pw.next = "";
          pw.confirm = "";
        }
      }
    };

    const submitAgent = async () => {
      if (props.onCreateAgent && agentForm.name.trim()) {
        await props.onCreateAgent({ ...agentForm });
        agentForm.name = "";
      }
    };

    const runSelectedAgent = async (agentId) => {
      if (props.onRunAgent && agentRunPrompt.value.trim()) {
        const savedPrompt = props.store.prompt;
        props.store.prompt = agentRunPrompt.value.trim();
        await props.onRunAgent(agentId);
        props.store.prompt = savedPrompt;
      }
    };

    const submitKey = () => {
      if (props.onCreateSecretKey) {
        props.onCreateSecretKey(keyLabel.value.trim() || "Default API Key");
        keyLabel.value = "Workspace API Key";
      }
    };

    return { tabs, pw, keyLabel, agentForm, agentRunPrompt, showTab, saveDefaults, submitPassword, submitKey, submitAgent, runSelectedAgent };
  },
};
