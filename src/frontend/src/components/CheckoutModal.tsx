import { useEffect, useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Coins,
  CreditCard,
  Receipt,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Wallet,
  X,
} from "lucide-react";
import {
  BillingPlan,
  CheckoutActionResult,
  CheckoutReceipt,
  MfsPaymentPayload,
  PaymentMethod,
  QuotaStatus,
  SubscriptionInfo,
  UserProfile,
} from "../types/ai";
import {
  BDT_PER_USD,
  MFS_METHODS,
  formatBdt,
  formatCreditsBdtUsd,
  formatUsd,
  getPaymentMethodLabel,
  isValidTnxid,
  normalizeTnxid,
  resolvePlanBdt,
  usdToBdtNumber,
} from "../services/payment";

interface CheckoutModalProps {
  open: boolean;
  initialMode?: "credits" | "plans";
  initialPlanSlug?: string | null;
  user: UserProfile | null;
  quota: QuotaStatus | null;
  subscription: SubscriptionInfo | null;
  plans: BillingPlan[];
  onClose: () => void;
  onTopup: (credits: number, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult>;
  onSubscribe: (planSlug: string, payment?: MfsPaymentPayload) => Promise<CheckoutActionResult>;
  onOpenBilling: () => void;
}

const CREDIT_PACKS = [
  { credits: 100, priceUsd: "1.00", tag: "Starter" },
  { credits: 500, priceUsd: "5.00", tag: "Popular" },
  { credits: 2000, priceUsd: "20.00", tag: "Studio" },
  { credits: 5000, priceUsd: "50.00", tag: "Scale" },
];

export function CheckoutModal({
  open,
  initialMode = "credits",
  initialPlanSlug = null,
  user,
  quota,
  subscription,
  plans,
  onClose,
  onTopup,
  onSubscribe,
  onOpenBilling,
}: CheckoutModalProps) {
  const [mode, setMode] = useState<"credits" | "plans">(initialMode);
  const [creditsInput, setCreditsInput] = useState("500");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("bkash");
  const [tnxidInput, setTnxidInput] = useState("");
  const [selectedPlanSlug, setSelectedPlanSlug] = useState<string | null>(initialPlanSlug);
  const [busy, setBusy] = useState(false);
  const [modalError, setModalError] = useState("");
  const [receipt, setReceipt] = useState<CheckoutReceipt | null>(null);

  useEffect(() => {
    if (!open) return;
    setMode(initialMode);
    setCreditsInput("500");
    setTnxidInput("");
    setModalError("");
    setReceipt(null);
    setBusy(false);

    if (initialPlanSlug && plans.some((p) => p.slug === initialPlanSlug)) {
      setSelectedPlanSlug(initialPlanSlug);
    } else {
      const currentSlug = subscription?.plan.slug;
      const nextUpgrade = plans.find((p) => p.slug !== currentSlug);
      setSelectedPlanSlug(nextUpgrade?.slug ?? currentSlug ?? plans[0]?.slug ?? null);
    }
  }, [open, initialMode, initialPlanSlug, plans, subscription?.plan.slug]);

  if (!open) return null;

  const currentBalance = quota?.remaining_credits ?? 0;
  const trimmedCredits = creditsInput.trim();
  const isWholeInt = /^\d+$/.test(trimmedCredits);
  const parsedCredits = isWholeInt ? Number(trimmedCredits) : 0;
  const creditsValid = isWholeInt && parsedCredits >= 10 && parsedCredits <= 100000;

  let creditsValidationMsg = "";
  if (!trimmedCredits || !isWholeInt) {
    creditsValidationMsg = "Enter a whole number of credits (10 to 100,000).";
  } else if (parsedCredits < 10) {
    creditsValidationMsg = "Minimum checkout purchase is 10 credits (৳12.00).";
  } else if (parsedCredits > 100000) {
    creditsValidationMsg = "Maximum single checkout purchase is 100,000 credits (৳120,000.00).";
  }

  const estimatedUsd = creditsValid ? (parsedCredits * 0.01).toFixed(2) : "0.00";
  const estimatedBdt = creditsValid ? usdToBdtNumber(estimatedUsd) : 0;
  const projectedCreditBalance = currentBalance + (creditsValid ? parsedCredits : 0);

  const selectedPlan = plans.find((p) => p.slug === selectedPlanSlug) ?? null;
  const isSelectedCurrent = Boolean(selectedPlan && subscription?.plan.slug === selectedPlan.slug);
  const selectedIsFree = selectedPlan ? Number(selectedPlan.monthly_price_usd) === 0 : false;
  const selectedPlanBdt = selectedPlan ? resolvePlanBdt(selectedPlan) : 0;
  const planCreditsGrant = selectedPlan ? (selectedIsFree ? 0 : selectedPlan.monthly_credits) : 0;
  const projectedPlanBalance = currentBalance + planCreditsGrant;

  const tnxidClean = normalizeTnxid(tnxidInput);
  const tnxidValid = isValidTnxid(tnxidClean);
  const selectedWalletMeta = MFS_METHODS.find((m) => m.id === paymentMethod) ?? MFS_METHODS[0];

  const canCheckoutCredits = Boolean(creditsValid && tnxidValid && !busy);
  const canCheckoutPlan = Boolean(
    selectedPlan && !isSelectedCurrent && (selectedIsFree || tnxidValid) && !busy
  );

  const handleCheckoutCredits = async () => {
    if (!canCheckoutCredits) return;
    setBusy(true);
    setModalError("");
    try {
      const res = await onTopup(parsedCredits, {
        currency: "BDT",
        amount_bdt: estimatedBdt.toFixed(2),
        payment_method: paymentMethod,
        tnxid: tnxidClean,
      });
      if (res.ok) {
        if (res.receipt) {
          setReceipt(res.receipt);
        } else {
          onClose();
        }
      } else {
        setModalError(res.error || "Deposit failed. Please verify TrxID and try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  const handleCheckoutPlan = async () => {
    if (!selectedPlan || !canCheckoutPlan) return;
    setBusy(true);
    setModalError("");
    try {
      const paymentPayload: MfsPaymentPayload | undefined = selectedIsFree
        ? undefined
        : {
            currency: "BDT",
            amount_bdt: selectedPlanBdt.toFixed(2),
            payment_method: paymentMethod,
            tnxid: tnxidClean,
          };
      const res = await onSubscribe(selectedPlan.slug, paymentPayload);
      if (res.ok) {
        if (res.receipt) {
          setReceipt(res.receipt);
        } else {
          onClose();
        }
      } else {
        setModalError(res.error || "Plan activation failed. Please check TrxID and try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  const switchTab = (nextMode: "credits" | "plans") => {
    setMode(nextMode);
    setModalError("");
    setReceipt(null);
  };

  const renderMfsPaymentInputs = (bdtDue: number) => (
    <div className="space-y-2.5 rounded-xl bg-slate-50/90 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 p-3">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
          <Wallet className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" />
          <span>BDT MFS Payment Method</span>
        </span>
        <span className="font-mono font-bold text-cyan-700 dark:text-cyan-300">
          {formatBdt(bdtDue)} BDT
        </span>
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        {MFS_METHODS.map((m) => {
          const active = paymentMethod === m.id;
          return (
            <button
              key={m.id}
              type="button"
              disabled={busy}
              onClick={() => {
                setPaymentMethod(m.id);
                setModalError("");
              }}
              className={`py-1.5 px-2 rounded-lg border text-xs font-semibold transition ${
                active
                  ? m.activeClass
                  : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:border-slate-300"
              }`}
            >
              {m.label}
            </button>
          );
        })}
      </div>

      <div className="text-[11px] text-slate-600 dark:text-slate-400">
        Pay <span className="font-mono font-semibold text-slate-900 dark:text-white">{formatBdt(bdtDue)}</span> via{" "}
        <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedWalletMeta.accountHint}</span>, then enter your TrxID below:
      </div>

      <div>
        <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
          {selectedWalletMeta.label} Transaction ID (TrxID)
        </label>
        <input
          type="text"
          disabled={busy}
          value={tnxidInput}
          onChange={(e) => {
            setTnxidInput(e.target.value.toUpperCase());
            setModalError("");
          }}
          placeholder={`e.g. ${selectedWalletMeta.label.toUpperCase()}8X92K4M1`}
          className={`w-full rounded-xl bg-white dark:bg-slate-950 border px-3 py-2 text-xs font-mono uppercase text-slate-900 dark:text-white focus:outline-none ${
            tnxidInput && !tnxidValid
              ? "border-rose-400 dark:border-rose-500/70 focus:border-rose-500"
              : "border-slate-300 dark:border-slate-700 focus:border-cyan-500"
          }`}
        />
        {tnxidInput && !tnxidValid && (
          <p className="mt-1 text-[11px] text-rose-600 dark:text-rose-400">
            TrxID must be at least 6 alphanumeric characters.
          </p>
        )}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/55 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg max-h-[92vh] overflow-y-auto rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-6 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShoppingBag className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
              <span>Balance &amp; Deposit (BDT · USD)</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              @{user?.username || "user"} · Balance:{" "}
              <span className="font-mono font-semibold text-slate-900 dark:text-white">
                {formatCreditsBdtUsd(currentBalance)}
              </span>{" "}
              · Rate: <span className="font-mono">$1 = ৳{BDT_PER_USD}</span>
            </p>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            aria-label="Close checkout"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {!receipt ? (
          <>
            <div className="grid grid-cols-2 gap-1.5 p-1 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
              <button
                type="button"
                disabled={busy}
                onClick={() => switchTab("credits")}
                className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                  mode === "credits"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                <Coins className="w-3.5 h-3.5" />
                <span>Top Up Balance</span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => switchTab("plans")}
                className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                  mode === "plans"
                    ? "bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                <CreditCard className="w-3.5 h-3.5" />
                <span>Upgrade Plan</span>
              </button>
            </div>

            {modalError && (
              <div className="rounded-xl bg-rose-50 dark:bg-rose-500/15 border border-rose-200 dark:border-rose-500/40 px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-200 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
                <span className="break-words">{modalError}</span>
              </div>
            )}

            {mode === "credits" ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {CREDIT_PACKS.map((pack) => {
                    const selected = isWholeInt && parsedCredits === pack.credits;
                    const packBdt = usdToBdtNumber(pack.priceUsd);
                    return (
                      <button
                        key={pack.credits}
                        type="button"
                        disabled={busy}
                        onClick={() => {
                          setCreditsInput(String(pack.credits));
                          setModalError("");
                        }}
                        className={`rounded-xl p-2.5 border text-left transition ${
                          selected
                            ? "border-cyan-500 bg-cyan-50/70 dark:bg-cyan-500/15"
                            : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-slate-50/70 dark:bg-slate-950/60"
                        }`}
                      >
                        <div className="text-[10px] font-semibold text-cyan-600 dark:text-cyan-400">
                          {pack.tag}
                        </div>
                        <div className="font-mono text-sm font-bold text-slate-900 dark:text-white">
                          {formatBdt(packBdt)}
                        </div>
                        <div className="text-[11px] font-mono text-slate-700 dark:text-slate-300">
                          {formatUsd(pack.priceUsd)} USD
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                          +{pack.credits.toLocaleString()} units
                        </div>
                      </button>
                    );
                  })}
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                    Custom Balance Units (৳1.20 BDT / $0.01 USD per unit · min 10)
                  </label>
                  <input
                    type="number"
                    min={10}
                    max={100000}
                    step={10}
                    disabled={busy}
                    value={creditsInput}
                    onChange={(e) => {
                      setCreditsInput(e.target.value);
                      setModalError("");
                    }}
                    className={`w-full rounded-xl bg-slate-50 dark:bg-slate-950 border px-3.5 py-2 text-sm font-mono text-slate-900 dark:text-white focus:outline-none ${
                      creditsValidationMsg
                        ? "border-rose-400 dark:border-rose-500/70 focus:border-rose-500"
                        : "border-slate-300 dark:border-slate-700 focus:border-cyan-500"
                    }`}
                  />
                  {creditsValidationMsg && (
                    <p className="mt-1 text-[11px] text-rose-600 dark:text-rose-400">
                      {creditsValidationMsg}
                    </p>
                  )}
                </div>

                {renderMfsPaymentInputs(estimatedBdt)}

                <div className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3 space-y-1.5 text-xs">
                  <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                    <span>Value Added</span>
                    <span className="font-mono font-semibold text-slate-900 dark:text-white">
                      {creditsValid ? formatCreditsBdtUsd(parsedCredits, { signed: true, compact: true }) : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                    <span>Projected Balance</span>
                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatCreditsBdtUsd(projectedCreditBalance, { compact: true })}
                    </span>
                  </div>
                  <div className="border-t border-slate-200 dark:border-slate-800 pt-1.5 flex items-center justify-between">
                    <span className="font-medium text-slate-700 dark:text-slate-300">
                      Total ({selectedWalletMeta.label})
                    </span>
                    <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">
                      {formatBdt(estimatedBdt)} <span className="text-[11px] font-normal text-slate-500">({formatUsd(estimatedUsd)} USD)</span>
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  disabled={!canCheckoutCredits}
                  onClick={() => void handleCheckoutCredits()}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-45 disabled:cursor-not-allowed shadow-sm"
                >
                  <Check className="w-4 h-4" />
                  <span>
                    {busy
                      ? "Processing Deposit..."
                      : !creditsValid
                      ? "Enter Valid Amount"
                      : !tnxidValid
                      ? `Enter ${selectedWalletMeta.label} TrxID`
                      : `Complete Deposit · ${formatBdt(estimatedBdt)}`}
                  </span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="space-y-2 max-h-48 overflow-y-auto pr-0.5">
                  {plans.map((plan) => {
                    const isCurrent = subscription?.plan.slug === plan.slug;
                    const isSelected = selectedPlan?.slug === plan.slug;
                    const freeSwitch = Number(plan.monthly_price_usd) === 0;
                    const planBdt = resolvePlanBdt(plan);
                    return (
                      <button
                        key={plan.slug}
                        type="button"
                        disabled={busy || isCurrent}
                        onClick={() => {
                          setSelectedPlanSlug(plan.slug);
                          setModalError("");
                        }}
                        className={`w-full text-left rounded-xl p-3 border flex items-center justify-between gap-3 transition ${
                          isCurrent
                            ? "border-emerald-500/40 bg-emerald-50/40 dark:bg-emerald-500/10 opacity-85 cursor-default"
                            : isSelected
                            ? "border-cyan-500 bg-cyan-50/60 dark:bg-cyan-500/15 ring-1 ring-cyan-500/30"
                            : "border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/60 hover:border-slate-300 dark:hover:border-slate-700"
                        }`}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-display font-semibold text-sm text-slate-900 dark:text-white">
                              {plan.name}
                            </span>
                            {isCurrent && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300">
                                Current
                              </span>
                            )}
                            {!isCurrent && isSelected && (
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-300">
                                Selected
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] font-mono text-slate-600 dark:text-slate-400 mt-0.5">
                            {freeSwitch
                              ? `Free switch · ${plan.daily_request_limit.toLocaleString()} req/day`
                              : `Usage Value: ${formatCreditsBdtUsd(plan.monthly_credits, { signed: true, compact: true })} · ${plan.daily_request_limit.toLocaleString()} req/day`}
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className="font-mono text-sm font-bold text-slate-900 dark:text-white">
                            {formatBdt(planBdt)}
                            <span className="text-[10px] font-normal text-slate-500">/mo</span>
                          </div>
                          <div className="text-[10px] font-mono text-slate-500">
                            ${plan.monthly_price_usd}/mo
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {selectedPlan && !isSelectedCurrent && !selectedIsFree && renderMfsPaymentInputs(selectedPlanBdt)}

                {selectedPlan && (
                  <div className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                      <span>Selected Plan</span>
                      <span className="font-semibold text-slate-900 dark:text-white">
                        {selectedPlan.name}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                      <span>Usage Value Added</span>
                      <span className="font-mono font-semibold text-slate-900 dark:text-white">
                        {selectedIsFree
                          ? `${formatCreditsBdtUsd(0, { compact: true })} (free switch)`
                          : formatCreditsBdtUsd(planCreditsGrant, { signed: true, compact: true })}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                      <span>Projected Balance</span>
                      <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                        {formatCreditsBdtUsd(projectedPlanBalance, { compact: true })}
                      </span>
                    </div>
                    <div className="border-t border-slate-200 dark:border-slate-800 pt-1.5 flex items-center justify-between">
                      <span className="font-medium text-slate-700 dark:text-slate-300">Monthly Charge</span>
                      <span className="font-mono text-sm font-bold text-slate-900 dark:text-white">
                        {formatBdt(selectedPlanBdt)} <span className="text-[11px] font-normal text-slate-500">(${selectedPlan.monthly_price_usd}/mo)</span>
                      </span>
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  disabled={!canCheckoutPlan}
                  onClick={() => void handleCheckoutPlan()}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-45 disabled:cursor-not-allowed shadow-sm"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>
                    {busy
                      ? "Activating Plan..."
                      : isSelectedCurrent
                      ? "Select Another Plan"
                      : !selectedIsFree && !tnxidValid
                      ? `Enter ${selectedWalletMeta.label} TrxID`
                      : selectedPlan
                      ? `Confirm & Activate · ${formatBdt(selectedPlanBdt)}`
                      : "Select a Plan"}
                  </span>
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="space-y-4">
            <div
              className={`rounded-xl border p-4 flex items-center justify-between gap-3 ${
                receipt.pending
                  ? "bg-amber-50/70 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/35"
                  : "bg-emerald-50/70 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/35"
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={`w-9 h-9 rounded-xl text-white flex items-center justify-center shrink-0 ${
                    receipt.pending ? "bg-amber-500" : "bg-emerald-600"
                  }`}
                >
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <div
                    className={`font-display font-bold text-sm ${
                      receipt.pending
                        ? "text-amber-900 dark:text-amber-200"
                        : "text-emerald-900 dark:text-emerald-200"
                    }`}
                  >
                    {receipt.pending ? "Payment Submitted · Pending Admin Approval" : "Deposit Complete"}
                  </div>
                  <div
                    className={`text-xs truncate ${
                      receipt.pending
                        ? "text-amber-700 dark:text-amber-300"
                        : "text-emerald-700 dark:text-emerald-300"
                    }`}
                  >
                    {receipt.title}
                  </div>
                </div>
              </div>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold shrink-0 ${
                  receipt.pending
                    ? "bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-200"
                    : "bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                }`}
              >
                <ShieldCheck className="w-3 h-3" />
                <span>{receipt.pending ? "Pending Review" : receipt.verified ? "Verified" : "Recorded"}</span>
              </span>
            </div>

            <div className="rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3.5 space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                <span className="flex items-center gap-1.5">
                  <Receipt className="w-3.5 h-3.5" />
                  <span>{receipt.pending ? "Request ID" : receipt.kind === "plan" ? "Invoice Number" : "Reference ID"}</span>
                </span>
                <span className="font-mono font-semibold text-slate-900 dark:text-white">
                  {receipt.reference}
                </span>
              </div>
              {receipt.paymentMethod && (
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>Payment Method</span>
                  <span className="font-semibold text-slate-900 dark:text-white">
                    {getPaymentMethodLabel(receipt.paymentMethod)}
                  </span>
                </div>
              )}
              {receipt.tnxid && (
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>TrxID</span>
                  <span className="font-mono font-semibold text-cyan-700 dark:text-cyan-300">
                    {receipt.tnxid}
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                <span>Amount Paid</span>
                <span className="font-mono font-semibold text-slate-900 dark:text-white">
                  {formatBdt(receipt.amountBdt ?? usdToBdtNumber(receipt.amountUsd))} ({formatUsd(receipt.amountUsd)} USD)
                </span>
              </div>
              <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                <span>{receipt.pending ? "Value Upon Approval" : "Value Added"}</span>
                <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                  {receipt.creditsAdded > 0
                    ? formatCreditsBdtUsd(receipt.creditsAdded, { signed: true, compact: true })
                    : formatCreditsBdtUsd(0, { compact: true })}
                </span>
              </div>
              {typeof receipt.dailyLimit === "number" && (
                <div className="flex items-center justify-between text-slate-600 dark:text-slate-400">
                  <span>Daily Request Limit</span>
                  <span className="font-mono text-slate-900 dark:text-white">
                    {receipt.dailyLimit.toLocaleString()} req/day
                  </span>
                </div>
              )}
              <div className="border-t border-slate-200 dark:border-slate-800 pt-2 flex items-center justify-between">
                <span className="font-medium text-slate-700 dark:text-slate-300">
                  {receipt.pending ? "Current Balance" : "Updated Balance"}
                </span>
                <span className="font-mono text-sm font-bold text-cyan-700 dark:text-cyan-300">
                  {formatCreditsBdtUsd(receipt.balanceAfter)}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:opacity-95 text-white text-xs font-semibold"
              >
                Done
              </button>
              <button
                type="button"
                onClick={() => {
                  onOpenBilling();
                  onClose();
                }}
                className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Billing &amp; Invoices
              </button>
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>bKash · Nagad · Rocket · Upay verified sync</span>
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              onOpenBilling();
              onClose();
            }}
            className="text-indigo-600 dark:text-cyan-400 hover:underline font-medium disabled:opacity-40"
          >
            View Billing &amp; Quota
          </button>
        </div>
      </div>
    </div>
  );
}
