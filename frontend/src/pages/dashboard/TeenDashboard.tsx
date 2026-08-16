import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../api/auth";
import type { AccountView, ExchangeQuote, Loan, Transaction } from "../../api/types";
import { Sparkline } from "../../components/charts";
import { Badge, EmptyState } from "../../components/ui";
import { formatDateTime, formatDuration, formatMoney, kindEmoji, kindLabel } from "../../utils/format";
import { ConvertPanel, ExchangeStrip, LoansCard, MoneyCard, ScreenCard, BorrowCard } from "./shared";
import { CoinStack } from "../../components/art/Scene";

/** Full-detail dashboard for the teenager (and the default for adults viewing as kid). */
export default function TeenDashboard({
  account,
  onChanged,
}: {
  account: AccountView;
  onChanged: () => void;
}) {
  const { user } = useAuth();
  const [quote, setQuote] = useState<ExchangeQuote | null>(null);
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);

  function load() {
    api.get<ExchangeQuote>("/api/v1/exchange/quote").then(setQuote).catch(() => {});
    api
      .get<Transaction[]>(`/api/v1/accounts/${account.id}/transactions?limit=200`)
      .then(setTxs)
      .catch(() => {});
    api.get<Loan[]>("/api/v1/loans").then(setLoans).catch(() => {});
  }
  useEffect(load, [account.id]);

  const moneySeries = [...txs]
    .filter((t) => t.ledger === "money")
    .reverse()
    .map((t) => t.balance_after);
  const screenSeries = [...txs]
    .filter((t) => t.ledger === "screen")
    .reverse()
    .map((t) => t.balance_after);
  const refreshed = () => {
    onChanged();
    load();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">
            Hey {user?.display_name} {account.avatar}
          </h1>
          <p className="text-sm font-bold text-ink/45">your money &amp; screen-time bank</p>
        </div>
        <Badge tone="lav">teen view</Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-3">
          <MoneyCard account={account} />
          <div className="card !py-3">
            <p className="mb-1 text-xs font-bold text-ink/45">balance history</p>
            <Sparkline data={moneySeries} stroke="#F17FB6" fill="rgba(241,127,182,.15)" />
          </div>
        </div>
        <div className="flex flex-col gap-3">
          <ScreenCard account={account} />
          <div className="card !py-3">
            <p className="mb-1 text-xs font-bold text-ink/45">screen time history</p>
            <Sparkline data={screenSeries} stroke="#6FB8E8" fill="rgba(111,184,232,.15)" width={220} />
          </div>
        </div>
      </div>

      {quote && <ExchangeStrip quote={quote} />}
      {quote && (account.can_convert || user?.role === "admin") && (
        <ConvertPanel account={account} quote={quote} onDone={refreshed} />
      )}
      {quote && <BorrowCard account={account} quote={quote} onDone={refreshed} />}
      <LoansCard account={account} loans={loans} onChanged={refreshed} />

      <div className="card">
        <p className="font-extrabold">Recent activity</p>
        {txs.length === 0 ? (
          <EmptyState title="No transactions yet" hint="When Mom or Dad deposits, it shows up here.">
            <CoinStack size={90} />
          </EmptyState>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-bold text-ink/40">
                  <th className="pb-2 pr-3">when</th>
                  <th className="pb-2 pr-3">what</th>
                  <th className="pb-2 pr-3 text-right">amount</th>
                  <th className="pb-2 text-right">balance</th>
                </tr>
              </thead>
              <tbody>
                {txs.slice(0, 12).map((t) => (
                  <tr key={t.id} className="border-t border-ink/5">
                    <td className="py-2.5 pr-3 font-bold text-ink/50">{formatDateTime(t.created_at)}</td>
                    <td className="py-2.5 pr-3 font-bold">
                      <span className="mr-1.5">{kindEmoji(t.kind)}</span>
                      {kindLabel(t.kind)}
                      {t.note && <span className="ml-1.5 font-normal text-ink/40">{t.note}</span>}
                    </td>
                    <td
                      className={`py-2.5 pr-3 text-right font-extrabold tabular ${
                        t.delta >= 0 ? "text-mint-deep" : "text-red-400"
                      }`}
                    >
                      {t.ledger === "money" || t.ledger === "debt"
                        ? `${t.delta >= 0 ? "+" : ""}${formatMoney(t.delta)}`
                        : `${t.delta >= 0 ? "+" : "-"}${formatDuration(Math.abs(t.delta))}`}
                    </td>
                    <td className="py-2.5 text-right font-bold text-ink/60 tabular">
                      {t.ledger === "money" || t.ledger === "debt"
                        ? formatMoney(t.balance_after)
                        : formatDuration(t.balance_after)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
