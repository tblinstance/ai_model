/**
 * Vue 3 CDN Backend Neural Training Studio Component.
 * Enables training across tiers/backends, bulk JSON corpus import, sample CRUD, evaluation, and checkpoint audit.
 */
window.TrainingPanelComponent = {
  props: [
    "store",
    "onTrainEngine",
    "onTrainAll",
    "onResetTraining",
    "onRefreshTraining",
    "onCreateSample",
    "onBulkUploadJson",
    "onDeleteSample",
    "onEvaluatePrompt",
  ],
  template: `
    <div class="space-y-5">
      <!-- Top Controls Card -->
      <section class="glass-panel rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="font-display font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
              <i data-lucide="brain-circuit" class="w-4 h-4 text-indigo-600 dark:text-indigo-400"></i>
              <span>tblinc AI Neural Training Studio</span>
            </h2>
            <p class="text-xs text-slate-600 dark:text-slate-400">
              Train tblinc AI engines on built-in corpora and custom Dataset samples.
            </p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              @click="onRefreshTraining && onRefreshTraining()"
              :disabled="store.trainingBusy"
              class="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 disabled:opacity-50"
            >
              Refresh Status
            </button>
            <button
              type="button"
              @click="onResetTraining && onResetTraining()"
              :disabled="store.trainingBusy"
              class="px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-500/15 hover:bg-rose-100 dark:hover:bg-rose-500/25 border border-rose-200 dark:border-rose-500/35 text-xs font-semibold text-rose-700 dark:text-rose-300 disabled:opacity-50"
            >
              Reset Checkpoints
            </button>
          </div>
        </div>

        <!-- KPI Strip -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
            <div class="text-[11px] text-slate-500">Corpus Dataset Size</div>
            <div class="font-mono text-lg font-bold text-slate-900 dark:text-white">
              {{ (store.trainingStatus?.dataset_size || 0).toLocaleString() }}
            </div>
          </div>
          <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
            <div class="text-[11px] text-slate-500">Learned Intents</div>
            <div class="font-mono text-lg font-bold text-cyan-600 dark:text-cyan-400">
              {{ (store.trainingStatus?.learned_intents || []).length }}
            </div>
          </div>
          <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
            <div class="text-[11px] text-slate-500">Saved Checkpoints</div>
            <div class="font-mono text-lg font-bold text-indigo-600 dark:text-indigo-400">
              {{ (store.trainingCheckpoints || []).length }}
            </div>
          </div>
          <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
            <div class="text-[11px] text-slate-500">Engine State</div>
            <div class="font-mono text-sm font-bold pt-1" :class="store.trainingStatus?.trained ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'">
              {{ store.trainingStatus?.trained ? 'TRAINED & READY' : 'UNTRAINED' }}
            </div>
          </div>
        </div>

        <!-- Hyperparameters & Actions -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs pt-1 border-t border-slate-200 dark:border-slate-800">
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Tier</label>
            <select v-model="store.activeTier" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100">
              <option value="flash">tblinc Flash (64d / 2L)</option>
              <option value="pro">tblinc Pro (128d / 4L)</option>
              <option value="advance">tblinc Advance (256d / 6L)</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Cloud Engine</label>
            <select v-model="store.activeBackend" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100">
              <option value="numpy">tblinc Cloud Core (Fast Compute)</option>
              <option value="pytorch">tblinc Cloud Flash Engine</option>
              <option value="tensorflow">tblinc Cloud Pro Engine</option>
              <option value="keras">tblinc Cloud Advance Engine</option>
              <option value="hybrid">tblinc Cloud Ensemble (All Engines)</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Epochs (1-100)</label>
            <input v-model.number="store.trainingConfig.epochs" type="number" min="1" max="100" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 font-mono text-slate-900 dark:text-slate-100" />
          </div>
          <div>
            <label class="block text-[11px] font-mono text-slate-500 mb-1">Learning Rate</label>
            <input v-model.number="store.trainingConfig.learningRate" type="number" step="0.001" min="0.0001" max="0.5" class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 font-mono text-slate-900 dark:text-slate-100" />
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-4 text-xs text-slate-700 dark:text-slate-300">
            <label class="inline-flex items-center gap-1.5 cursor-pointer">
              <input v-model="store.trainingConfig.includeBuiltin" type="checkbox" class="rounded border-slate-300 dark:border-slate-700" />
              <span>Include Cloud Training Corpus</span>
            </label>
            <label class="inline-flex items-center gap-1.5 cursor-pointer">
              <input v-model="store.trainingConfig.includeConversations" type="checkbox" class="rounded border-slate-300 dark:border-slate-700" />
              <span>Include Recent Conversations</span>
            </label>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              @click="onTrainEngine && onTrainEngine()"
              :disabled="store.trainingBusy"
              class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
            >
              <i data-lucide="play" class="w-3.5 h-3.5"></i>
              <span>{{ store.trainingBusy ? 'Training...' : 'Train Tier (' + store.activeTier.toUpperCase() + ')' }}</span>
            </button>
            <button
              type="button"
              @click="onTrainAll && onTrainAll()"
              :disabled="store.trainingBusy"
              class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
            >
              <i data-lucide="layers" class="w-3.5 h-3.5"></i>
              <span>{{ store.trainingBusy ? 'Training...' : 'Train All Tiers' }}</span>
            </button>
          </div>
        </div>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <!-- Custom Sample + Big JSON Corpus Importer -->
        <section class="glass-panel rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white">Cloud Dataset &amp; Batch Import</h3>
              <p class="text-[11px] text-slate-500">Save individual Q&amp;A/code/media pairs or upload a training dataset file into tblinc Cloud Storage.</p>
            </div>
            <label class="cursor-pointer px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold inline-flex items-center gap-1.5">
              <i data-lucide="upload" class="w-3.5 h-3.5"></i>
              <span>Import JSON / JSONL / TXT</span>
              <input type="file" accept=".json,.jsonl,.txt" @change="handleJsonFile" class="hidden" />
            </label>
          </div>

          <form @submit.prevent="submitSample" class="space-y-2.5 text-xs">
            <input v-model="sampleForm.prompt" type="text" required placeholder="Training prompt (e.g. create orbital ripple gif)..." class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-slate-900 dark:text-slate-100" />
            <textarea v-model="sampleForm.response" rows="3" required placeholder="Target response or runnable code snippet..." class="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2.5 text-slate-900 dark:text-slate-100"></textarea>
            <div class="grid grid-cols-2 gap-2">
              <select v-model="sampleForm.intent" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100">
                <option v-for="intentOpt in intentOptions" :key="intentOpt" :value="intentOpt">{{ intentOpt }}</option>
              </select>
              <select v-model="sampleForm.task" class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1.5 text-slate-900 dark:text-slate-100">
                <option value="chat">chat</option>
                <option value="images">images</option>
                <option value="video">video</option>
                <option value="code">code</option>
              </select>
            </div>
            <button type="submit" :disabled="store.trainingBusy" class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold disabled:opacity-50">
              Save Sample to Cloud Dataset
            </button>
          </form>

          <div class="space-y-1.5 max-h-56 overflow-y-auto pr-1">
            <div v-for="rec in (store.trainingSamples || [])" :key="'tsamp-' + rec.id" class="rounded-lg bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-2.5 flex items-start justify-between gap-2 text-xs">
              <div class="min-w-0 flex-1">
                <div class="font-semibold text-slate-900 dark:text-white truncate">{{ rec.prompt }}</div>
                <div class="text-[11px] font-mono text-cyan-700 dark:text-cyan-400">{{ rec.task }} · {{ rec.intent }}</div>
              </div>
              <button type="button" @click="onDeleteSample && onDeleteSample(rec.id)" class="text-slate-400 hover:text-rose-500 p-1">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
              </button>
            </div>
            <div v-if="!(store.trainingSamples || []).length" class="text-[11px] text-slate-500 text-center py-3">
              No custom Cloud Dataset samples yet; built-in corpus ({{ store.trainingStatus?.dataset_size || 0 }}) is active.
            </div>
          </div>
        </section>

        <!-- Prompt Evaluation & Checkpoints -->
        <section class="glass-panel rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-4">
          <div>
            <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white">Evaluate Trained Classifier &amp; Checkpoints</h3>
            <p class="text-[11px] text-slate-500">Test intent classification and inspect saved weights in tblinc Cloud Checkpoints.</p>
          </div>

          <form @submit.prevent="submitEval" class="flex flex-wrap gap-2 text-xs">
            <input v-model="evalPrompt" type="text" required placeholder="Prompt to evaluate (e.g. create vortex animated gif)..." class="flex-1 min-w-[200px] rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-slate-900 dark:text-slate-100" />
            <button type="submit" :disabled="store.trainingBusy" class="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold disabled:opacity-50">
              Evaluate
            </button>
          </form>

          <div v-if="store.trainingEvalResult" class="rounded-xl bg-slate-50 dark:bg-slate-950/75 border border-cyan-200 dark:border-cyan-500/35 p-3 space-y-1 text-xs">
            <div class="font-mono text-cyan-700 dark:text-cyan-300 font-semibold">
              Intent: {{ store.trainingEvalResult.predicted_intent }} ({{ (store.trainingEvalResult.intent_confidence * 100).toFixed(1) }}%) · Match: {{ (store.trainingEvalResult.matched_sample_score * 100).toFixed(0) }}%
            </div>
            <div class="text-slate-600 dark:text-slate-300">{{ store.trainingEvalResult.generated_preview }}</div>
          </div>

          <div class="space-y-1.5 max-h-64 overflow-y-auto pr-1 text-xs">
            <div class="text-[11px] font-mono text-slate-500 uppercase">Saved Weight &amp; Index Files</div>
            <div v-for="ck in (store.trainingCheckpoints || [])" :key="ck.filename" class="rounded-lg bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 px-3 py-2 flex items-center justify-between gap-2">
              <span class="font-mono text-slate-900 dark:text-white truncate">{{ ck.filename }}</span>
              <span class="font-mono text-[11px] text-slate-500 shrink-0">{{ ck.backend }} · {{ ck.tier }} · {{ (ck.size_bytes / 1024).toFixed(1) }} KB</span>
            </div>
            <div v-if="!(store.trainingCheckpoints || []).length" class="text-[11px] text-slate-500 text-center py-3">
              No saved checkpoint files on disk yet.
            </div>
          </div>
        </section>
      </div>

      <!-- Training Run History -->
      <section class="glass-panel rounded-2xl p-5 border border-slate-200 dark:border-slate-800 space-y-3">
        <h3 class="font-display font-semibold text-sm text-slate-900 dark:text-white">Cloud Training Run History</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500 uppercase">
                <th class="py-2 pr-3">ID</th>
                <th class="py-2 pr-3">Scope / Tier</th>
                <th class="py-2 pr-3">Backend</th>
                <th class="py-2 pr-3">Dataset</th>
                <th class="py-2 pr-3">Duration</th>
                <th class="py-2 pr-3">Results</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in (store.trainingHistory || [])" :key="'trun-' + run.id" class="border-b border-slate-100 dark:border-slate-800/60">
                <td class="py-2 pr-3 font-mono text-slate-600 dark:text-slate-400">{{ String(run.training_id || '').slice(0, 8) }}</td>
                <td class="py-2 pr-3 font-mono uppercase text-slate-900 dark:text-white">{{ run.scope }} · {{ run.tier }}</td>
                <td class="py-2 pr-3 font-mono text-cyan-700 dark:text-cyan-300">{{ run.backend }} ({{ run.epochs }} ep)</td>
                <td class="py-2 pr-3 font-mono">{{ run.dataset_size }}</td>
                <td class="py-2 pr-3 font-mono">{{ Number(run.duration_ms || 0).toFixed(0) }} ms</td>
                <td class="py-2 pr-3 font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
                  {{ (run.backends_trained || []).map((b) => b.backend + ':' + (b.accuracy * 100).toFixed(0) + '%').join(' · ') }}
                </td>
              </tr>
              <tr v-if="!(store.trainingHistory || []).length">
                <td colspan="6" class="py-4 text-center text-slate-500">No training runs recorded yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
  setup(props) {
    const { ref } = Vue;
    const sampleForm = ref({ prompt: "", response: "", intent: "general", task: "chat" });
    const evalPrompt = ref("");
    const intentOptions = [
      "greeting", "math_compute", "code_python", "code_typescript",
      "code_sql", "code_bash", "debugging", "architecture",
      "image_generation", "video_generation", "conversation_memory",
      "billing_quota", "training_ml", "comparison", "explanation", "general",
    ];

    const submitSample = async () => {
      if (!sampleForm.value.prompt.trim() || !sampleForm.value.response.trim()) return;
      if (props.onCreateSample) {
        await props.onCreateSample(Object.assign({}, sampleForm.value));
        sampleForm.value.prompt = "";
        sampleForm.value.response = "";
      }
    };

    const submitEval = async () => {
      if (!evalPrompt.value.trim() || !props.onEvaluatePrompt) return;
      await props.onEvaluatePrompt(evalPrompt.value.trim());
    };

    const handleJsonFile = async (e) => {
      const file = e.target && e.target.files ? e.target.files[0] : null;
      if (!file || !props.onBulkUploadJson) return;
      await props.onBulkUploadJson(file);
      e.target.value = "";
    };

    return { sampleForm, evalPrompt, intentOptions, submitSample, submitEval, handleJsonFile };
  },
};

