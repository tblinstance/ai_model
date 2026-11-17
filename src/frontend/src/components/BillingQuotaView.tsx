import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Check, CheckCircle2, CreditCard, Mail, PlusCircle, Receipt, ShieldCheck, ShoppingBag, User } from "lucide-react";
import {
  BillingPlan,
  CheckoutActionResult,
  InvoiceItem,
  MfsPaymentPayload,
  MfsPaymentRequestItem,
  ModelTier,
  PaymentMethod,
  QuotaStatus,
  SubscriptionInfo,
  UserProfile,
} from "../types/ai";
import {
  MFS_METHODS,
  formatBdt,
  formatCreditsBdtUsd,
  getPaymentMethodLabel,
  isValidTnxid,
  normalizeTnxid,
  resolvePlanBdt,
  usdToBdtNumber,
} from "../services/payment";

interface BillingQuotaViewProps {
  user: UserProfile | null;
  plans: BillingPlan[];
  subscription: SubscriptionInfo | null;
  quota: QuotaStatus | null;
  invoices?: InvoiceItem[];
  mfsRequests?: MfsPaymentRequestItem[];
  activeTier: ModelTier;
  authenticated: boolean;
  onSubscribe: (slug: string, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult | void>;
  onTopup: (credits: number, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult | void>;
  onOpenCheckout?: () => void;
  onOpenCheckoutPlan?: (planSlug: string) => void;
  onUpdateProfile: (email: string) => Promise<void>;
  onOpenAuth: () => void;
}

export function BillingQuotaView({
  user,
  plans,
  subscription,
  quota,
  invoices = [],
  mfsRequests = [],
  activeTier,
  authenticated,
  onSubscribe,
  onTopup,
  onOpenCheckout,
  onOpenCheckoutPlan,
  onUpdateProfile,
  onOpenAuth,
}: BillingQuotaViewProps) {
  const [topupCredits, setTopupCredits] = useState(500);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("bkash");
  const [tnxidDraft, setTnxidDraft] = useState("");
  const [emailDraft, setEmailDraft] = useState(user?.email || "");
  const [savingProfile, setSavingProfile] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const topupValid = Number.isInteger(topupCredits) && topupCredits >= 10 && topupCredits <= 100000;
  const cleanTnxid = normalizeTnxid(tnxidDraft);
  const tnxidValid = isValidTnxid(cleanTnxid);
  const topupBdt = topupValid ? usdToBdtNumber((topupCredits * 0.01).toFixed(2)) : 0;

  const handleTopupClick = async () => {
    if (busyAction || !authenticated || !topupValid || !tnxidValid) return;
    setBusyAction("topup");
    try {
      const res = await onTopup(topupCredits, {
        currency: "BDT",
        amount_bdt: topupBdt.toFixed(2),
        payment_method: paymentMethod,
        tnxid: cleanTnxid,
      });
      if (!res || res.ok) {
        setTnxidDraft("");
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handlePlanClick = async (slug: string, isCurrent: boolean) => {
    if (busyAction || !authenticated || isCurrent) return;
    if (onOpenCheckoutPlan) {
      onOpenCheckoutPlan(slug);
      return;
    }
    setBusyAction(slug);
    try {
      await onSubscribe(slug);
    } finally {
      setBusyAction(null);
    }
  };

  useEffect(() => {
    setEmailDraft(user?.email || "");
  }, [user?.email]);

  const pct = quota
    ? Math.min(100, Math.round((quota.remaining_credits / Math.max(1, quota.total_credits)) * 100))
    : 0;
  const roleLabel = user?.is_superuser ? "Superuser" : user?.is_staff ? "Staff" : "Member";
  const initials = (user?.username || "U").slice(0, 2).toUpperCase();

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailDraft.trim() || savingProfile) return;
    setSavingProfile(true);
    try {
      await onUpdateProfile(emailDraft.trim());
    } finally {
      setSavingProfile(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Compact Account Profile + Quota Summary Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Account Profile Card (sm) */}
        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 text-white font-display font-bold text-xs flex items-center justify-center shrink-0">
                {initials}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-semibold text-sm text-slate-900 dark:text-white truncate">
                    @{user?.username || "guest"}
                  </span>
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 font-mono text-[10px]">
                    <ShieldCheck className="w-2.5 h-2.5" />
                    {roleLabel}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  ID #{user?.id ?? "-"}
                  {user?.date_joined ? ` · Joined ${user.date_joined.slice(0, 10)}` : ""}
                </div>
              </div>
            </div>
            <User className="w-4 h-4 text-slate-400 shrink-0" />
          </div>

          {authenticated ? (
            <form onSubmit={handleSaveProfile} className="flex items-center gap-2 pt-1">
              <div className="relative flex-1 min-w-0">
                <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={emailDraft}
                  onChange={(e) => setEmailDraft(e.target.value)}
                  placeholder="Account email"
                  className="w-full rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 pl-8 pr-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:border-cyan-500 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={savingProfile || !emailDraft.trim() || emailDraft.trim() === (user?.email || "")}
                className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-45 shrink-0"
              >
                <Check className="w-3 h-3" />
                <span>{savingProfile ? "Saving" : "Save"}</span>
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={onOpenAuth}
              className="px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-semibold"
            >
              Sign In to View Profile
            </button>
          )}
        </div>

        {/* Quota & Top-Up Card (sm) */}
        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="font-display text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <CreditCard className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                <span>Quota &amp; Balance</span>
              </h2>
              <p className="text-[11px] text-slate-600 dark:text-slate-400">
                Plan: <span className="text-cyan-700 dark:text-cyan-300 font-semibold">{subscription?.plan.name || "Free"}</span>
                {quota ? ` · ${quota.daily_requests}/${quota.max_daily_requests} daily calls` : ""}
              </p>
            </div>
            {quota && (
              <span className="font-mono text-xs font-semibold text-slate-900 dark:text-white">
                {formatCreditsBdtUsd(quota.remaining_credits, { compact: true })} / {formatCreditsBdtUsd(quota.total_credits, { compact: true })}
              </span>
            )}
          </div>

          {quota && (
            <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
          )}

          {authenticated && (
            <div className="space-y-2 pt-0.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1">
                  {MFS_METHODS.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setPaymentMethod(m.id)}
                      className={`px-2 py-0.5 rounded-md text-[11px] font-semibold border transition ${
                        paymentMethod === m.id
                          ? m.activeClass
                          : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300"
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                <div className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
                  {topupValid
                    ? `${formatBdt(topupBdt)} BDT ($${(topupCredits * 0.01).toFixed(2)})`
                    : <span className="text-rose-600 dark:text-rose-400">Enter ৳12.00 – ৳120,000.00 BDT ($0.10 – $1,000.00)</span>}
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <input
                  type="text"
                  value={tnxidDraft}
                  onChange={(e) => setTnxidDraft(e.target.value.toUpperCase())}
                  placeholder="TrxID (e.g. BKASH8X9K)"
                  className="flex-1 min-w-[135px] rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 px-2.5 py-1 text-xs font-mono uppercase text-slate-900 dark:text-white"
                />
                <input
                  type="number"
                  min={10}
                  max={100000}
                  step={50}
                  value={topupCredits}
                  onChange={(e) => setTopupCredits(Number(e.target.value))}
                  className="w-20 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 px-2 py-1 text-xs font-mono text-slate-900 dark:text-white"
                />
                <button
                  type="button"
                  disabled={!topupValid || !tnxidValid || Boolean(busyAction)}
                  onClick={() => void handleTopupClick()}
                  className="px-3 py-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1 disabled:opacity-45 disabled:cursor-not-allowed"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  <span>{busyAction === "topup" ? "Adding..." : "Top Up"}</span>
                </button>
                {onOpenCheckout && (
                  <button
                    type="button"
                    onClick={onOpenCheckout}
                    className="px-2.5 py-1 rounded-lg border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-1"
                  >
                    <ShoppingBag className="w-3.5 h-3.5" />
                    <span>Deposit</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Compact Plan Cards (sm) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {plans.map((plan) => {
          const isCurrent = subscription?.plan.slug === plan.slug;
          return (
            <motion.div
              key={plan.slug}
              whileHover={{ y: -2 }}
              className={`rounded-xl p-3.5 border flex flex-col justify-between gap-2.5 bg-white/90 dark:bg-slate-900/70 shadow-xs dark:shadow-none ${
                isCurrent ? "border-cyan-500/70 dark:border-cyan-500/60 shadow-sm shadow-cyan-500/10" : "border-slate-200 dark:border-slate-800"
              }`}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-1.5">
                  <span className="font-display font-bold text-sm text-slate-900 dark:text-white truncate">
                    {plan.name}
                  </span>
                  {isCurrent && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 shrink-0" />}
                </div>
                <div className="text-lg font-display font-bold text-slate-900 dark:text-white">
                  {formatBdt(resolvePlanBdt(plan))}
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 font-normal">/mo</span>
                  <div className="text-[10px] font-mono font-normal text-slate-500 dark:text-slate-400">
                    ${plan.monthly_price_usd}/mo USD
                  </div>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-snug">
                  {plan.description}
                </p>
                <div className="pt-1 space-y-0.5 text-[11px] font-mono text-slate-700 dark:text-slate-300">
                  <div>{formatCreditsBdtUsd(plan.monthly_credits, { compact: true })} · {plan.daily_request_limit.toLocaleString()} req/day</div>
                  <div className="truncate">Tiers: {plan.allowed_tiers.join(", ")}</div>
                  {plan.allowed_tiers.includes(activeTier) && (
                    <div className="text-emerald-700 dark:text-emerald-300">Supports {activeTier.toUpperCase()}</div>
                  )}
                </div>
              </div>

              <button
                type="button"
                disabled={!authenticated || isCurrent || Boolean(busyAction)}
                onClick={() => void handlePlanClick(plan.slug, isCurrent)}
                className={`w-full py-1.5 rounded-lg text-xs font-semibold disabled:cursor-not-allowed ${
                  isCurrent
                    ? "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30"
                    : "bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40"
                }`}
              >
                {isCurrent ? "Current Plan" : busyAction === plan.slug ? "Activating..." : "Deposit"}
              </button>
            </motion.div>
          );
        })}
      </div>

      {/* Submitted BDT MFS Payment Requests */}
      {authenticated && (
        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>Submitted BDT Payment Requests (bKash · Nagad · Rocket · Upay)</span>
            </h3>
            <span className="text-[11px] font-mono text-slate-500">{mfsRequests.length} requests</span>
          </div>
          {mfsRequests.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-1.5 pr-3">Req</th>
                    <th className="py-1.5 pr-3">Item</th>
                    <th className="py-1.5 pr-3">Method</th>
                    <th className="py-1.5 pr-3">TrxID</th>
                    <th className="py-1.5 pr-3">Value (BDT / USD)</th>
                    <th className="py-1.5 pr-3">Amount (BDT)</th>
                    <th className="py-1.5 pr-3">Status</th>
                    <th className="py-1.5 text-right">Note</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono text-[11px]">
                  {mfsRequests.slice(0, 12).map((req) => (
                    <tr key={req.id} className="text-slate-700 dark:text-slate-300">
                      <td className="py-1.5 pr-3 font-semibold text-slate-900 dark:text-white">#{req.id}</td>
                      <td className="py-1.5 pr-3 font-sans">
                        {req.kind === "plan" ? `${req.plan_name} Plan` : "Credits Pack"}
                      </td>
                      <td className="py-1.5 pr-3 font-sans">{getPaymentMethodLabel(req.payment_method)}</td>
                      <td className="py-1.5 pr-3 text-cyan-700 dark:text-cyan-300">{req.tnxid}</td>
                      <td className="py-1.5 pr-3 text-emerald-600 dark:text-emerald-400">
                        {formatCreditsBdtUsd(req.credits_requested, { signed: true, compact: true })}
                      </td>
                      <td className="py-1.5 pr-3">{formatBdt(req.amount_bdt)}</td>
                      <td className="py-1.5 pr-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            req.status === "approved"
                              ? "bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                              : req.status === "rejected"
                              ? "bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300"
                              : "bg-amber-100 dark:bg-amber-500/15 text-amber-800 dark:text-amber-300"
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="py-1.5 text-right font-sans text-slate-500 truncate max-w-[160px]">
                        {req.admin_note || (req.status === "pending" ? "Awaiting Admin Approval" : "—")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No submitted BDT wallet requests yet. Pay via bKash, Nagad, Rocket, or Upay in Deposit to submit a TrxID for Admin verification.
            </p>
          )}
        </div>
      )}

      {/* Invoices & Plan Receipts */}
      {authenticated && (
        <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-xs dark:shadow-none">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-display font-semibold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
              <Receipt className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>Invoices &amp; Plan Receipts</span>
            </h3>
            <span className="text-[11px] font-mono text-slate-500">{invoices.length} records</span>
          </div>
          {invoices.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-[11px] text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-1.5 pr-3">Invoice</th>
                    <th className="py-1.5 pr-3">Plan</th>
                    <th className="py-1.5 pr-3">Method</th>
                    <th className="py-1.5 pr-3">TrxID</th>
                    <th className="py-1.5 pr-3">Value (BDT / USD)</th>
                    <th className="py-1.5 pr-3">Amount (BDT)</th>
                    <th className="py-1.5 pr-3">Status</th>
                    <th className="py-1.5 text-right">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono text-[11px]">
                  {invoices.slice(0, 10).map((inv) => (
                    <tr key={inv.id} className="text-slate-700 dark:text-slate-300">
                      <td className="py-1.5 pr-3 font-semibold text-slate-900 dark:text-white">{inv.invoice_number}</td>
                      <td className="py-1.5 pr-3 font-sans">{inv.plan_name}</td>
                      <td className="py-1.5 pr-3 font-sans">{getPaymentMethodLabel(inv.payment_method)}</td>
                      <td className="py-1.5 pr-3 text-cyan-700 dark:text-cyan-300">{inv.tnxid || "—"}</td>
                      <td className="py-1.5 pr-3 text-emerald-600 dark:text-emerald-400">
                        {inv.credits_granted > 0
                          ? formatCreditsBdtUsd(inv.credits_granted, { signed: true, compact: true })
                          : formatCreditsBdtUsd(0, { compact: true })}
                      </td>
                      <td className="py-1.5 pr-3">{formatBdt(inv.amount_bdt ?? usdToBdtNumber(inv.amount_usd))}</td>
                      <td className="py-1.5 pr-3">
                        <span className="px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 text-[10px]">
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-1.5 text-right text-slate-500">{inv.created_at.slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No plan invoices yet. Plan activations and renewals generate itemized receipts here.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
