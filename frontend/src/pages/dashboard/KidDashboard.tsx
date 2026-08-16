import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../api/auth";
import type { AccountView, ExchangeQuote, Transaction } from "../../api/types";
import { Badge } from "../../components/ui";
import { Piggy } from "../../components/art/Piggy";
import { formatDateTime, formatDuration, formatMoney, kindEmoji, kindLabel } from "../../utils/format";
import { ConvertPanel, ExchangeStrip, MoneyCard, ScreenCard } from "./shared";

/** Elementary-school kid: bigger, simpler, friendlier. */
export default function KidDashboard({
  account,
  onChanged,
}: {
  account: AccountView;
  onChanged: () => void;
}) {
  const { user } = useAuth();
  const [quote, setQuote] = useState<ExchangeQuote | null>(null);
  const [txs, setTxs] = useState<Transaction[]>([]);

  useEffect(() => {
    api.get<ExchangeQuote>("/api/v1/exchange/quote").then(setQuote).catch(() => {});
    api
      .get<Transaction[]>(`/api/v1/accounts/${account.id}/transactions?limit=10`)
      .then(setTxs)
      .catch(() => {});
  }, [account.id]);

  const refreshed = () => {
    onChanged();
    api
      .get<Transaction[]>(`/api/v1/accounts/${account.id}/transactions?limit=10`)
      .then(setTxs)
      .catch(() => {});
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="page-title">Hi {user?.display_name}! {account.avatar}</h1>
        <Badge tone="mint">kid view</Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <MoneyCard account={account} big />
        <ScreenCard account={account} big />
      </div>

      {account.next_day_interest_cents > 0 && (
        <div className="card flex items-center gap-4 !bg-mintsoft !ring-mint/20">
          <Piggy mood="happy" size={72} animate={false} />
          <p className="font-bold">
            Your money is growing! 🌱 Every day you get a little extra — tomorrow{" "}
            <span className="text-mint-deep">+{formatMoney(account.next_day_interest_cents)}</span> just for
            saving!
          </p>
        </div>
      )}

      {quote && <ExchangeStrip quote={quote} />}
      {quote && (account.can_convert || user?.role === "admin") && (
        <ConvertPanel account={account} quote={quote} onDone={refreshed} />
      )}

      <div className="card">
        <p className="font-extrabold">What happened lately</p>
        <ul className="mt-3 flex flex-col gap-2.5">
          {txs.length === 0 && <p className="py-4 text-center text-sm font-bold text-ink/40">Nothing yet — wait for your first deposit! 🐷</p>}
          {txs.map((t) => (
            <li key={t.id} className="flex items-center gap-3 rounded-2xl bg-cream px-3 py-2.5">
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-white text-xl shadow-soft">
                {kindEmoji(t.kind)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-extrabold">{kindLabel(t.kind)}</p>
                <p className="text-xs font-bold text-ink/40">{formatDateTime(t.created_at)}</p>
              </div>
              <p
                className={`font-extrabold tabular ${t.delta >= 0 ? "text-mint-deep" : "text-red-400"}`}
              >
                {t.ledger === "screen"
                  ? `${t.delta >= 0 ? "+" : "-"}${formatDuration(Math.abs(t.delta))}`
                  : `${t.delta >= 0 ? "+" : ""}${formatMoney(t.delta)}`}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
