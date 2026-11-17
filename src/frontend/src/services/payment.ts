import { PaymentMethod } from "../types/ai";

export const BDT_PER_USD = 120;

export interface MfsMethodMeta {
  id: PaymentMethod;
  label: string;
  accountHint: string;
  activeClass: string;
}

export const MFS_METHODS: MfsMethodMeta[] = [
  {
    id: "bkash",
    label: "bKash",
    accountHint: "Send Money / Merchant · bKash Personal/Merchant",
    activeClass: "border-pink-500 bg-pink-50/80 dark:bg-pink-500/15 text-pink-700 dark:text-pink-300",
  },
  {
    id: "nagad",
    label: "Nagad",
    accountHint: "Send Money · Nagad Wallet",
    activeClass: "border-orange-500 bg-orange-50/80 dark:bg-orange-500/15 text-orange-700 dark:text-orange-300",
  },
  {
    id: "rocket",
    label: "Rocket",
    accountHint: "DBBL Rocket Mobile Wallet",
    activeClass: "border-purple-500 bg-purple-50/80 dark:bg-purple-500/15 text-purple-700 dark:text-purple-300",
  },
  {
    id: "upay",
    label: "Upay",
    accountHint: "Upay Digital Wallet",
    activeClass: "border-amber-500 bg-amber-50/80 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300",
  },
];

export const USD_PER_CREDIT = 0.01;

export function usdToBdtNumber(amountUsd: string | number | undefined): number {
  const n = Number(amountUsd || 0);
  if (!Number.isFinite(n) || n <= 0) return 0;
  return Math.round(n * BDT_PER_USD * 100) / 100;
}

export function creditsToUsdNumber(credits: number | string | undefined): number {
  const n = Number(credits || 0);
  if (!Number.isFinite(n)) return 0;
  return Math.round(n * USD_PER_CREDIT * 100) / 100;
}

export function creditsToBdtNumber(credits: number | string | undefined): number {
  const usd = creditsToUsdNumber(credits);
  return Math.round(usd * BDT_PER_USD * 100) / 100;
}

export function formatUsd(amountUsd: string | number | undefined): string {
  const n = Number(amountUsd || 0);
  const safe = Number.isFinite(n) ? n : 0;
  return `$${safe.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatCreditsBdtUsd(
  credits: number | string | undefined,
  options?: { signed?: boolean; compact?: boolean }
): string {
  const raw = Number(credits || 0);
  const safe = Number.isFinite(raw) ? raw : 0;
  const sign = options?.signed ? (safe > 0 ? "+" : safe < 0 ? "-" : "") : safe < 0 ? "-" : "";
  const absVal = Math.abs(safe);
  const usd = creditsToUsdNumber(absVal);
  const bdt = Math.round(usd * BDT_PER_USD * 100) / 100;
  if (options?.compact) {
    return `${sign}${formatBdt(bdt)} (${formatUsd(usd)})`;
  }
  return `${sign}${formatBdt(bdt)} BDT · ${formatUsd(usd)} USD`;
}

export function resolvePlanBdt(plan: { monthly_price_usd: string; monthly_price_bdt?: string }): number {
  if (plan.monthly_price_bdt !== undefined && plan.monthly_price_bdt !== null) {
    const parsed = Number(plan.monthly_price_bdt);
    if (Number.isFinite(parsed)) return parsed;
  }
  return usdToBdtNumber(plan.monthly_price_usd);
}

export function formatBdt(amountBdt: string | number | undefined): string {
  const n = Number(amountBdt || 0);
  return `৳${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function normalizeTnxid(raw: string): string {
  return raw.trim().toUpperCase();
}

export function isValidTnxid(raw: string): boolean {
  return /^[A-Z0-9_-]{6,64}$/.test(normalizeTnxid(raw));
}

export function getPaymentMethodLabel(method?: string | null): string {
  const clean = (method || "").trim().toLowerCase();
  const found = MFS_METHODS.find((m) => m.id === clean);
  if (found) return found.label;
  if (!clean) return "—";
  return clean.toUpperCase();
}

