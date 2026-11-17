/**
 * Vue 3 CDN Backend Admin Control Panel for managing Users, Billings, MFS TrxID Approvals (BDT), and Transactions.
 */
window.AdminControlPanelComponent = {
  props: [
    "store",
    "onRefreshAdmin",
    "onApproveMfs",
    "onRejectMfs",
    "onGrantCredits",
    "onClearBalance",
    "onSwitchUserPlan",
  ],
  template: `
    <section class="glass-panel rounded-2xl p-4 sm:p-5 space-y-4 border border-slate-200 dark:border-slate-800">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 class="font-display font-bold text-base text-slate-900 dark:text-white flex items-center gap-2">
            <i data-lucide="shield-check" class="w-4 h-4 text-cyan-600 dark:text-cyan-400"></i>
            <span>Admin Users, Billing &amp; MFS Control</span>
          </h2>
          <p class="text-[11px] text-slate-600 dark:text-slate-400">
            Verify member bKash / Nagad / Rocket / Upay TrxIDs, approve BDT payments, manage member plans, and audit transactions.
          </p>
        </div>
        <button
          type="button"
          :disabled="store.adminBusy"
          @click="onRefreshAdmin && onRefreshAdmin()"
          class="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-100 disabled:opacity-45"
        >
          {{ store.adminBusy ? 'Refreshing...' : 'Refresh Queue' }}
        </button>
      </div>

      <!-- Summary KPI Strip -->
      <div v-if="store.adminOverview?.summary" class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
          <div class="text-[11px] text-slate-500">Total Users</div>
          <div class="font-mono text-lg font-bold text-slate-900 dark:text-white">{{ store.adminOverview.summary.total_users }}</div>
        </div>
        <div class="rounded-xl border p-3" :class="store.adminOverview.summary.pending_requests > 0 ? 'bg-amber-50/70 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/40' : 'bg-slate-50 dark:bg-slate-950/70 border-slate-200 dark:border-slate-800'">
          <div class="text-[11px] text-slate-500">Pending MFS Approvals</div>
          <div class="font-mono text-lg font-bold" :class="store.adminOverview.summary.pending_requests > 0 ? 'text-amber-700 dark:text-amber-300' : 'text-slate-900 dark:text-white'">
            {{ store.adminOverview.summary.pending_requests }}
          </div>
        </div>
        <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
          <div class="text-[11px] text-slate-500">Settled Volume (BDT)</div>
          <div class="font-mono text-lg font-bold text-emerald-600 dark:text-emerald-400">
            ৳{{ Number(store.adminOverview.summary.total_revenue_bdt || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
          </div>
        </div>
        <div class="rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
          <div class="text-[11px] text-slate-500">Member Balance (BDT / USD)</div>
          <div class="font-mono text-sm sm:text-base font-bold text-cyan-600 dark:text-cyan-400">
            {{ formatCreditsBdtUsd(store.adminOverview.summary.total_credits_balance) }}
          </div>
        </div>
      </div>

      <!-- Sub-navigation Tabs -->
      <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 dark:border-slate-800 pb-2.5">
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="tab in adminTabs"
            :key="'atab-' + tab.id"
            type="button"
            @click="activeTab = tab.id"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition"
            :class="activeTab === tab.id ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'"
          >
            {{ tab.label }}
            <span v-if="tab.id === 'mfs' && store.adminOverview?.summary?.pending_requests" class="ml-1 px-1.5 py-0.2 rounded-full bg-amber-400 text-slate-950 text-[10px] font-mono">
              {{ store.adminOverview.summary.pending_requests }}
            </span>
          </button>
        </div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search @user or TrxID..."
          class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-3 py-1 text-xs text-slate-900 dark:text-white focus:border-cyan-500 focus:outline-none w-52"
        />
      </div>

      <!-- 1. MFS Payment Approvals -->
      <div v-if="activeTab === 'mfs'" class="space-y-3">
        <div class="flex flex-wrap items-center gap-1.5 text-xs">
          <button
            v-for="st in ['all', 'pending', 'approved', 'rejected']"
            :key="'st-' + st"
            type="button"
            @click="statusFilter = st"
            class="px-2.5 py-1 rounded-lg border text-[11px] font-mono uppercase transition"
            :class="statusFilter === st ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 font-semibold' : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'"
          >
            {{ st }}
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th class="py-2 pr-3">Req</th>
                <th class="py-2 pr-3">Member</th>
                <th class="py-2 pr-3">Order</th>
                <th class="py-2 pr-3">Method</th>
                <th class="py-2 pr-3">TrxID</th>
                <th class="py-2 pr-3">Amount (BDT)</th>
                <th class="py-2 pr-3">Credits</th>
                <th class="py-2 pr-3">Status</th>
                <th class="py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 dark:divide-slate-800/70">
              <tr v-for="req in filteredMfsRequests" :key="'mfs-row-' + req.id" class="text-slate-800 dark:text-slate-200">
                <td class="py-2 pr-3 font-mono font-semibold">#{{ req.id }}</td>
                <td class="py-2 pr-3 font-medium">@{{ req.username }}</td>
                <td class="py-2 pr-3">{{ req.kind === 'plan' ? (req.plan_name + ' Plan') : 'Credit Pack' }}</td>
                <td class="py-2 pr-3 uppercase font-semibold">{{ req.payment_method }}</td>
                <td class="py-2 pr-3 font-mono text-cyan-700 dark:text-cyan-300">{{ req.tnxid }}</td>
                <td class="py-2 pr-3 font-mono">৳{{ Number(req.amount_bdt || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td class="py-2 pr-3 font-mono text-emerald-600 dark:text-emerald-400">+{{ Number(req.credits_requested).toLocaleString() }}</td>
                <td class="py-2 pr-3">
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase"
                    :class="req.status === 'approved' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' : (req.status === 'rejected' ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300' : 'bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300')"
                  >
                    {{ req.status }}
                  </span>
                </td>
                <td class="py-2 text-right whitespace-nowrap">
                  <div v-if="req.status === 'pending'" class="inline-flex items-center gap-1.5">
                    <button
                      type="button"
                      :disabled="store.adminBusy"
                      @click="onApproveMfs && onApproveMfs(req.id)"
                      class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold disabled:opacity-45"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      :disabled="store.adminBusy"
                      @click="onRejectMfs && onRejectMfs(req.id)"
                      class="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[11px] font-semibold disabled:opacity-45"
                    >
                      Reject
                    </button>
                  </div>
                  <span v-else class="text-[11px] text-slate-500">
                    {{ req.reviewed_by_username ? ('@' + req.reviewed_by_username) : 'Done' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!filteredMfsRequests.length" class="text-xs text-slate-500 py-5 text-center">
            No MFS payment requests match this filter.
          </p>
        </div>
      </div>

      <!-- 2. Users & Member Balances -->
      <div v-if="activeTab === 'users'" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th class="py-2 pr-3">User</th>
              <th class="py-2 pr-3">Role</th>
              <th class="py-2 pr-3">Active Plan</th>
              <th class="py-2 pr-3">Balance / Total</th>
              <th class="py-2 pr-3">Switch Plan</th>
              <th class="py-2 text-right">Balance Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-800/70">
            <tr v-for="u in filteredUsers" :key="'adm-u-' + u.id" class="text-slate-800 dark:text-slate-200">
              <td class="py-2 pr-3">
                <div class="font-semibold text-slate-900 dark:text-white">@{{ u.username }}</div>
                <div class="text-[10px] text-slate-500 font-mono">{{ u.email || 'no email' }}</div>
              </td>
              <td class="py-2 pr-3 font-mono text-[10px]">
                <span class="px-1.5 py-0.5 rounded" :class="u.is_superuser || u.is_staff ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'">
                  {{ u.is_superuser ? 'Superuser' : (u.is_staff ? 'Admin' : 'Member') }}
                </span>
              </td>
              <td class="py-2 pr-3">{{ u.plan_name }}</td>
              <td class="py-2 pr-3 font-mono">
                <span class="font-semibold text-cyan-700 dark:text-cyan-300">{{ formatCreditsBdtUsd(u.remaining_credits, { compact: true }) }}</span>
                / {{ formatCreditsBdtUsd(u.total_credits, { compact: true }) }}
              </td>
              <td class="py-2 pr-3">
                <div class="inline-flex items-center gap-1">
                  <select
                    v-model="planSelection[u.id]"
                    class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2 py-1 text-[11px]"
                  >
                    <option v-for="pl in store.plans" :key="'plopt-' + u.id + '-' + pl.slug" :value="pl.slug">
                      {{ pl.name }}
                    </option>
                  </select>
                  <button
                    type="button"
                    :disabled="store.adminBusy || !planSelection[u.id] || planSelection[u.id] === u.plan_slug"
                    @click="onSwitchUserPlan && onSwitchUserPlan(u.id, planSelection[u.id])"
                    class="px-2 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-semibold disabled:opacity-40"
                  >
                    Set
                  </button>
                </div>
              </td>
              <td class="py-2 text-right">
                <div class="inline-flex items-center gap-1">
                  <input
                    v-model.number="grantAmounts[u.id]"
                    type="number"
                    min="1"
                    max="1000000"
                    placeholder="500"
                    class="w-20 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 px-2 py-1 text-[11px] font-mono"
                  />
                  <button
                    type="button"
                    :disabled="store.adminBusy || !(Number(grantAmounts[u.id]) >= 1)"
                    @click="triggerGrant(u.id)"
                    class="px-2.5 py-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-[10px] font-semibold disabled:opacity-40"
                  >
                    + Grant
                  </button>
                  <button
                    type="button"
                    :disabled="store.adminBusy || !(Number(u.remaining_credits) > 0)"
                    @click="triggerClear(u)"
                    class="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-[10px] font-semibold disabled:opacity-40"
                  >
                    Clear
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 3. All Users Invoices -->
      <div v-if="activeTab === 'invoices'" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th class="py-2 pr-3">Invoice</th>
              <th class="py-2 pr-3">Member</th>
              <th class="py-2 pr-3">Plan</th>
              <th class="py-2 pr-3">Method</th>
              <th class="py-2 pr-3">TrxID</th>
              <th class="py-2 pr-3">Value (BDT / USD)</th>
              <th class="py-2 pr-3">Amount (BDT)</th>
              <th class="py-2 text-right">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-800/70 font-mono text-[11px]">
            <tr v-for="inv in filteredInvoices" :key="'adm-inv-' + inv.id" class="text-slate-700 dark:text-slate-300">
              <td class="py-2 pr-3 font-semibold text-slate-900 dark:text-white">{{ inv.invoice_number }}</td>
              <td class="py-2 pr-3 font-sans">@{{ inv.username }}</td>
              <td class="py-2 pr-3 font-sans">{{ inv.plan_name }}</td>
              <td class="py-2 pr-3 uppercase font-sans">{{ inv.payment_method || '—' }}</td>
              <td class="py-2 pr-3 text-cyan-700 dark:text-cyan-300">{{ inv.tnxid || '—' }}</td>
              <td class="py-2 pr-3 text-emerald-600 dark:text-emerald-400">{{ formatCreditsBdtUsd(inv.credits_granted, { signed: true, compact: true }) }}</td>
              <td class="py-2 pr-3">৳{{ Number(inv.amount_bdt ?? (Number(inv.amount_usd || 0) * 120)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
              <td class="py-2 text-right">{{ inv.status }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!filteredInvoices.length" class="text-xs text-slate-500 py-5 text-center">No invoices recorded.</p>
      </div>

      <!-- 4. All Users Transactions -->
      <div v-if="activeTab === 'transactions'" class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th class="py-2 pr-3">Reference</th>
              <th class="py-2 pr-3">Member</th>
              <th class="py-2 pr-3">Type</th>
              <th class="py-2 pr-3">Method</th>
              <th class="py-2 pr-3">TrxID</th>
              <th class="py-2 pr-3">Value (BDT / USD)</th>
              <th class="py-2 pr-3">Balance After</th>
              <th class="py-2 text-right">Amount (BDT)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 dark:divide-slate-800/70 font-mono text-[11px]">
            <tr v-for="tx in filteredTransactions" :key="'adm-tx-' + tx.reference_id" class="text-slate-700 dark:text-slate-300">
              <td class="py-2 pr-3 text-slate-500">{{ tx.reference_id }}</td>
              <td class="py-2 pr-3 font-sans">@{{ tx.username }}</td>
              <td class="py-2 pr-3">{{ tx.tx_type }}</td>
              <td class="py-2 pr-3 uppercase font-sans">{{ tx.payment_method || '—' }}</td>
              <td class="py-2 pr-3 text-cyan-700 dark:text-cyan-300">{{ tx.tnxid || '—' }}</td>
              <td class="py-2 pr-3 font-semibold" :class="tx.credits_delta >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-300'">
                {{ formatCreditsBdtUsd(tx.credits_delta, { signed: true, compact: true }) }}
              </td>
              <td class="py-2 pr-3">{{ formatCreditsBdtUsd(tx.balance_after, { compact: true }) }}</td>
              <td class="py-2 text-right">৳{{ Number(tx.amount_bdt ?? (Number(tx.amount_usd || 0) * 120)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!filteredTransactions.length" class="text-xs text-slate-500 py-5 text-center">No transactions recorded.</p>
      </div>
    </section>
  `,
  setup(props) {
    const { computed, reactive, ref, watch } = Vue;
    const activeTab = computed({
      get: () => props.store.adminTab || "mfs",
      set: (val) => {
        props.store.adminTab = val;
      },
    });
    const statusFilter = ref("all");
    const searchQuery = ref("");
    const planSelection = reactive({});
    const grantAmounts = reactive({});

    const adminTabs = [
      { id: "mfs", label: "MFS Approvals" },
      { id: "users", label: "Users & Balances" },
      { id: "invoices", label: "All Invoices" },
      { id: "transactions", label: "All Transactions" },
    ];

    watch(
      () => props.store.adminOverview?.users,
      (users) => {
        if (!Array.isArray(users)) return;
        for (const u of users) {
          planSelection[u.id] = u.plan_slug || "free";
          if (!grantAmounts[u.id]) grantAmounts[u.id] = 500;
        }
      },
      { immediate: true }
    );

    const normSearch = computed(() => searchQuery.value.trim().toLowerCase());

    const matchesSearch = (item) => {
      if (!normSearch.value) return true;
      const hay = [
        item.username,
        item.email,
        item.tnxid,
        item.payment_method,
        item.invoice_number,
        item.reference_id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(normSearch.value);
    };

    const filteredMfsRequests = computed(() => {
      const list = props.store.adminOverview?.mfs_requests || [];
      return list.filter(
        (r) =>
          (statusFilter.value === "all" || r.status === statusFilter.value) &&
          matchesSearch(r)
      );
    });

    const filteredUsers = computed(() => {
      const list = props.store.adminOverview?.users || [];
      return list.filter(matchesSearch);
    });

    const filteredInvoices = computed(() => {
      const list = props.store.adminOverview?.invoices || [];
      return list.filter(matchesSearch);
    });

    const filteredTransactions = computed(() => {
      const list = props.store.adminOverview?.transactions || [];
      return list.filter(matchesSearch);
    });

    const triggerGrant = (userId) => {
      const amt = Number(grantAmounts[userId]);
      if (props.onGrantCredits && amt >= 1) {
        props.onGrantCredits(userId, amt);
      }
    };

    const triggerClear = (u) => {
      if (!u || !(Number(u.remaining_credits) > 0) || !props.onClearBalance) return;
      if (window.confirm(`Clear balance for @${u.username} (${formatCreditsBdtUsd(u.remaining_credits)}) to 0?`)) {
        props.onClearBalance(u.id, u.username);
      }
    };

    const formatCreditsBdtUsd = (c, opts) => window.AIModelBilling.formatCreditsBdtUsd(c, opts);
    return {
      activeTab,
      statusFilter,
      searchQuery,
      adminTabs,
      planSelection,
      grantAmounts,
      filteredMfsRequests,
      filteredUsers,
      filteredInvoices,
      filteredTransactions,
      triggerGrant,
      triggerClear,
      formatCreditsBdtUsd,
    };
  },
};

