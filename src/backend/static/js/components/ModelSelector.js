/**
 * Vue 3 CDN component for switching between Flash, Pro, and Advance model tiers
 * and triggering neural training runs across PyTorch, TensorFlow, and Keras.
 */
window.ModelSelectorComponent = {
  props: ["store", "onTrainEngine", "onTrainAll"],
  template: `
    <section class="glass-panel rounded-2xl p-4 mb-5 space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Model Tier Architecture</h2>
          <p class="text-xs text-slate-600 dark:text-slate-400">Select inference depth across tblinc AI project tiers</p>
        </div>
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="text-slate-600 dark:text-slate-400">Cloud Engine:</span>
          <select v-model="store.activeBackend" class="bg-slate-50 dark:bg-slate-900/90 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1 text-slate-900 dark:text-slate-200 focus:outline-none">
            <option value="numpy">tblinc Cloud Core (Fast Compute)</option>
            <option value="pytorch">tblinc Cloud Flash Engine</option>
            <option value="tensorflow">tblinc Cloud Pro Engine</option>
            <option value="keras">tblinc Cloud Advance Engine</option>
            <option value="hybrid">tblinc Cloud Ensemble (All Engines)</option>
          </select>
          <button
            v-if="onTrainEngine"
            type="button"
            @click="onTrainEngine()"
            :disabled="store.trainingBusy"
            class="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold disabled:opacity-50 flex items-center gap-1.5 transition"
          >
            <i data-lucide="brain-circuit" class="w-3.5 h-3.5"></i>
            <span>{{ store.trainingBusy ? 'Training...' : 'Train Neural Engine' }}</span>
          </button>
          <button
            v-if="onTrainAll"
            type="button"
            @click="onTrainAll()"
            :disabled="store.trainingBusy"
            class="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold disabled:opacity-50 flex items-center gap-1.5 transition"
          >
            <i data-lucide="layers" class="w-3.5 h-3.5"></i>
            <span>{{ store.trainingBusy ? 'Training...' : 'Train All Tiers' }}</span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <button
          v-for="tier in tiers"
          :key="tier.id"
          @click="selectTier(tier.id)"
          class="tier-pill text-left rounded-xl p-3.5 border bg-slate-50/90 dark:bg-slate-900/60"
          :class="store.activeTier === tier.id ? tier.activeClass : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'"
        >
          <div class="flex items-center justify-between mb-1 gap-2">
            <span class="font-display font-semibold text-slate-900 dark:text-white">{{ tier.title }}</span>
            <div class="flex items-center gap-1.5">
              <span v-if="store.activeTier === tier.id" class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300">Active</span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded-full" :class="tier.badgeClass">{{ tier.tag }}</span>
            </div>
          </div>
          <p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{{ tier.subtitle }}</p>
        </button>
      </div>

      <div v-if="store.trainingResult || store.trainingStatus?.last_training" class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3 flex flex-wrap items-center justify-between gap-2 text-xs">
        <span class="font-mono text-slate-700 dark:text-slate-300">
          Checkpoint Ready · {{ (store.trainingResult || store.trainingStatus.last_training).dataset_size }} samples
        </span>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="st in (store.trainingResult || store.trainingStatus.last_training).backends_trained"
            :key="'tr-' + st.backend"
            class="px-2 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[11px]"
          >
            {{ st.backend }}: {{ (st.accuracy * 100).toFixed(0) }}% acc ({{ st.final_loss.toFixed(3) }} loss)
          </span>
        </div>
      </div>
    </section>
  `,
  setup(props) {
    const selectTier = (tierId) => {
      props.store.activeTier = tierId;
      props.store.modelDropdownOpen = false;
      localStorage.setItem("ai_model_backend_active_tier", tierId);
    };
    const tiers = [
      {
        id: "flash",
        title: "tblinc Flash",
        tag: "৳1.20–৳9.60 BDT ($0.01–$0.08)",
        subtitle: "tblinc AI — ultra-fast low-latency path",
        activeClass: "tier-pill-active-flash",
        badgeClass: "bg-cyan-100 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300",
      },
      {
        id: "pro",
        title: "tblinc Pro",
        tag: "৳3.60–৳24.00 BDT ($0.03–$0.20)",
        subtitle: "tblinc AI — balanced reasoning & production code",
        activeClass: "tier-pill-active-pro",
        badgeClass: "bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
      },
      {
        id: "advance",
        title: "tblinc Advance",
        tag: "৳7.20–৳43.20 BDT ($0.06–$0.36)",
        subtitle: "tblinc AI — complex synthesis & studio media",
        activeClass: "tier-pill-active-advance",
        badgeClass: "bg-purple-100 dark:bg-purple-500/15 text-purple-700 dark:text-purple-300",
      },
    ];
    return { tiers, selectTier };
  },
};
