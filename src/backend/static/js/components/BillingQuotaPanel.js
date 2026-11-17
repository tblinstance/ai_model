/**
 * Vue 3 CDN compact sidebar panel showing User Profile, Quota, Billing Plans, and Transactions.
 */
window.BillingQuotaPanelComponent = {
  props: ["store", "onSubscribe", "onOpenTopup", "onUpdateProfile", "onVerifyAccount"],
  template: `
    <aside class="space-y-3">
      <!-- Compact Account Profile Card (sm) -->
      <div class="glass-panel rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 text-white font-display font-bold text-xs flex items-center justify-center shrink-0">
              {{ (store.user?.username || 'U').slice(0, 2).toUpperCase() }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="font-display font-semibold text-xs text-slate-900 dark:text-white truncate">@{{ store.user?.username || 'guest' }}</span>
                <span class="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[10px]">
                  {{ store.user?.is_superuser ? 'Superuser' : (store.user?.is_staff ? 'Staff' : 'Member') }}
                </span>
              </div>
              <div class="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">
                ID #{{ store.user?.id || '-' }}{{ store.user?.date_joined ? (' · ' + String(store.user.date_joined).slice(0, 10)) : '' }}
              </div>
            </div>
          </div>
          <i data-lucide="user-check" class="w-4 h-4 text-cyan-600 dark:text-cyan-400 shrink-0"></i>
        </div>

        <form v-if="store.authenticated && onUpdateProfile" @submit.prevent="saveEmail" class="flex items-center gap-1.5">
          <input
            v-model="emailDraft"
            type="email"
            placeholder="Email address"
            class="flex-1 min-w-0 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2.5 py-1 text-xs text-slate-900 dark:text-slate-100 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            :disabled="!emailDraft.trim() || emailDraft.trim() === (store.user?.email || '')"
            class="px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold disabled:opacity-45 shrink-0"
          >
            Save
          </button>
        </form>
      </div>

      <!-- Compact Quota Card (sm) -->
      <div class="glass-panel rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between">
          <h3 class="font-display font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-1.5">
            <i data-lucide="gauge" class="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400"></i>
            <span>Quota Balance</span>
          </h3>
          <button
            v-if="store.authenticated"
            @click="onOpenTopup"
            class="text-[11px] px-2 py-0.5 rounded-lg bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 hover:bg-cyan-200 dark:hover:bg-cyan-500/30 font-semibold"
          >
            + Top Up
          </button>
        </div>

        <div v-if="store.quota" class="space-y-1.5">
          <div class="flex justify-between text-[11px] gap-2">
            <span class="text-slate-600 dark:text-slate-400">Balance</span>
            <span class="font-mono text-slate-900 dark:text-white font-medium truncate">{{ formatCreditsBdtUsd(store.quota.remaining_credits, { compact: true }) }}</span>
          </div>
          <div class="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all"
              :style="{ width: Math.min(100, Math.round((store.quota.remaining_credits / Math.max(1, store.quota.total_credits)) * 100)) + '%' }"
            ></div>
          </div>
          <div class="flex justify-between text-[11px] text-slate-600 dark:text-slate-400">
            <span>Daily: {{ store.quota.daily_requests }}/{{ store.quota.max_daily_requests }}</span>
            <span>{{ store.subscription?.plan?.name || 'Free' }}</span>
          </div>
        </div>
        <p v-else class="text-xs text-slate-600 dark:text-slate-400">Authenticate to view live quota &amp; billing.</p>
      </div>

      <!-- Compact Verification Card (sm) -->
      <div v-if="store.authenticated" class="glass-panel rounded-xl p-3 space-y-2">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <i data-lucide="shield-check" class="w-3.5 h-3.5" :class="store.verification?.verified ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'"></i>
            <span class="font-display font-semibold text-xs text-slate-900 dark:text-white">Account Verify</span>
          </div>
          <button
            v-if="onVerifyAccount"
            type="button"
            @click="onVerifyAccount(true)"
            class="text-[11px] px-2 py-0.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold"
          >
            Verify &amp; Sync
          </button>
        </div>
        <div v-if="store.verification" class="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-[10px] font-mono">
          <div class="rounded-lg px-2 py-1 border" :class="store.verification.profile?.verified ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300' : 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300'">
            Profile: {{ store.verification.profile?.verified ? 'OK' : 'Check' }}
          </div>
          <div class="rounded-lg px-2 py-1 border" :class="store.verification.billing?.verified ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300' : 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300'">
            Billing: {{ store.verification.billing?.verified ? 'OK' : 'Sync' }}
          </div>
          <div class="rounded-lg px-2 py-1 border" :class="store.verification.balance?.verified ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300' : 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300'">
            Balance: {{ store.verification.balance?.verified ? 'OK' : 'Mismatch' }}
          </div>
          <div class="rounded-lg px-2 py-1 border" :class="store.verification.checkout?.verified ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30 text-emerald-700 dark:text-emerald-300' : 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30 text-amber-700 dark:text-amber-300'">
            Deposit: {{ store.verification.checkout?.verified ? 'OK' : 'Check' }}
          </div>
        </div>
        <div v-if="store.verification?.issues?.length" class="text-[10px] font-mono text-amber-700 dark:text-amber-300">
          Issues: {{ store.verification.issues.join(', ') }}
        </div>
      </div>

      <!-- Compact Billing Plans (sm) -->
      <div class="glass-panel rounded-xl p-3 space-y-2">
        <h3 class="font-display font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-1.5">
          <i data-lucide="credit-card" class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400"></i>
          <span>Billing Plans</span>
        </h3>
        <div class="grid grid-cols-1 gap-1.5">
          <div v-for="plan in store.plans" :key="plan.slug" class="rounded-lg bg-slate-50 dark:bg-slate-900/70 border border-slate-200 dark:border-slate-800 p-2.5 flex items-center justify-between gap-2">
            <div class="min-w-0">
              <div class="text-xs font-semibold text-slate-900 dark:text-white truncate">{{ plan.name }}</div>
              <div class="text-[11px] font-mono text-slate-600 dark:text-slate-400">৳{{ Number(plan.monthly_price_bdt ?? (Number(plan.monthly_price_usd || 0) * 120)).toLocaleString() }}/mo (\${{ plan.monthly_price_usd }} USD) · {{ formatCreditsBdtUsd(plan.monthly_credits, { compact: true }) }}</div>
            </div>
            <button
              v-if="store.authenticated"
              type="button"
              :disabled="store.subscription?.plan?.slug === plan.slug"
              @click="onSubscribe(plan.slug)"
              class="px-2.5 py-1 rounded-lg text-[11px] font-semibold shrink-0 disabled:cursor-not-allowed"
              :class="store.subscription?.plan?.slug === plan.slug ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' : 'bg-indigo-600 hover:bg-indigo-500 text-white'"
            >
              {{ store.subscription?.plan?.slug === plan.slug ? 'Current' : 'Deposit' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Compact Invoices (sm) -->
      <div v-if="(store.invoices || []).length" class="glass-panel rounded-xl p-3 space-y-1.5">
        <h3 class="font-display font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-1.5">
          <i data-lucide="file-text" class="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400"></i>
          <span>Invoices</span>
        </h3>
        <div class="space-y-1 max-h-32 overflow-y-auto custom-scroll">
          <div v-for="inv in store.invoices.slice(0, 5)" :key="inv.invoice_number" class="flex justify-between items-center text-[11px] py-1 border-b border-slate-200 dark:border-slate-800/70 gap-2">
            <span class="font-mono text-slate-700 dark:text-slate-300 truncate">{{ inv.invoice_number }} · {{ inv.plan_name }}<span v-if="inv.tnxid" class="text-cyan-600 dark:text-cyan-400"> ({{ inv.payment_method?.toUpperCase() }} {{ inv.tnxid }})</span></span>
            <span class="font-mono text-emerald-600 dark:text-emerald-400 shrink-0">৳{{ Number(inv.amount_bdt ?? (Number(inv.amount_usd || 0) * 120)).toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <!-- Compact Recent Transactions (sm) -->
      <div class="glass-panel rounded-xl p-3 space-y-1.5">
        <h3 class="font-display font-semibold text-xs text-slate-900 dark:text-white flex items-center gap-1.5">
          <i data-lucide="receipt" class="w-3.5 h-3.5 text-purple-600 dark:text-purple-400"></i>
          <span>Recent Transactions</span>
        </h3>
        <div class="space-y-1 max-h-40 overflow-y-auto custom-scroll">
          <div v-for="tx in store.transactions.slice(0, 6)" :key="tx.reference_id" class="flex justify-between items-center text-[11px] py-1 border-b border-slate-200 dark:border-slate-800/70">
            <span class="text-slate-700 dark:text-slate-300 truncate max-w-[170px]">{{ tx.description }}</span>
            <span class="font-mono" :class="tx.credits_delta >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-300'">
              {{ formatCreditsBdtUsd(tx.credits_delta, { signed: true, compact: true }) }}
            </span>
          </div>
          <p v-if="!store.transactions.length" class="text-[11px] text-slate-500">No recent transactions.</p>
        </div>
      </div>
    </aside>
  `,
  setup(props) {
    const { ref, watch } = Vue;
    const emailDraft = ref(props.store.user?.email || "");
    watch(
      () => props.store.user?.email,
      (val) => {
        emailDraft.value = val || "";
      }
    );
    const saveEmail = () => {
      if (props.onUpdateProfile && emailDraft.value.trim()) {
        props.onUpdateProfile(emailDraft.value.trim());
      }
    };
    const formatCreditsBdtUsd = (c, opts) => window.AIModelBilling.formatCreditsBdtUsd(c, opts);
    return { emailDraft, saveEmail, formatCreditsBdtUsd };
  },
};
