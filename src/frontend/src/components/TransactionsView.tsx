import { Receipt } from "lucide-react";
import { TransactionItem } from "../types/ai";
import { formatBdt, formatCreditsBdtUsd, getPaymentMethodLabel, usdToBdtNumber } from "../services/payment";

interface TransactionsViewProps {
  transactions: TransactionItem[];
  authenticated: boolean;
  onOpenAuth: () => void;
}

export function TransactionsView({
  transactions,
  authenticated,
  onOpenAuth,
}: TransactionsViewProps) {
  if (!authenticated) {
    return (
      <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center space-y-3 shadow-xs dark:shadow-none">
        <Receipt className="w-10 h-10 text-cyan-600 dark:text-cyan-400 mx-auto" />
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-white">Sign In to View Transactions</h2>
        <button
          onClick={onOpenAuth}
          className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold"
        >
          Sign In
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white/90 dark:bg-slate-900/65 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4 shadow-xs dark:shadow-none">
      <h2 className="font-display text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
        <Receipt className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        <span>Credit & Billing Transaction Ledger</span>
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="py-2.5 pr-4">Reference</th>
              <th className="py-2.5 pr-4">Type</th>
              <th className="py-2.5 pr-4">Method</th>
              <th className="py-2.5 pr-4">TrxID</th>
              <th className="py-2.5 pr-4">Description</th>
              <th className="py-2.5 pr-4">Value (BDT / USD)</th>
              <th className="py-2.5 pr-4">Balance After</th>
              <th className="py-2.5">Amount (BDT)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800/70">
            {transactions.map((tx) => (
              <tr key={tx.reference_id} className="text-slate-800 dark:text-slate-200">
                <td className="py-2.5 pr-4 font-mono text-slate-500 dark:text-slate-400">{tx.reference_id}</td>
                <td className="py-2.5 pr-4 font-mono">{tx.tx_type}</td>
                <td className="py-2.5 pr-4 font-semibold">{getPaymentMethodLabel(tx.payment_method)}</td>
                <td className="py-2.5 pr-4 font-mono text-cyan-700 dark:text-cyan-300">{tx.tnxid || "—"}</td>
                <td className="py-2.5 pr-4">{tx.description}</td>
                <td
                  className={`py-2.5 pr-4 font-mono font-semibold ${
                    tx.credits_delta >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-700 dark:text-amber-300"
                  }`}
                >
                  {formatCreditsBdtUsd(tx.credits_delta, { signed: true, compact: true })}
                </td>
                <td className="py-2.5 pr-4 font-mono">{formatCreditsBdtUsd(tx.balance_after, { compact: true })}</td>
                <td className="py-2.5 font-mono">
                  {Number(tx.amount_bdt ?? usdToBdtNumber(tx.amount_usd)) > 0
                    ? formatBdt(tx.amount_bdt ?? usdToBdtNumber(tx.amount_usd))
                    : "৳0.00"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!transactions.length && (
          <p className="text-xs text-slate-500 py-6 text-center">No transactions recorded yet.</p>
        )}
      </div>
    </div>
  );
}

