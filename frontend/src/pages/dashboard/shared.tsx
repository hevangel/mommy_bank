import { useMemo, useState } from "react";
import { api } from "../../api/client";
import type { AccountView, ExchangeQuote, Loan } from "../../api/types";
import { CountUp } from "../../components/charts";
import { useToast } from "../../components/ui";
import {
  IconClock,
  IconExchange,
  IconRocket,
  IconSprout,
  IconWallet,
} from "../../components/art/icons";
import { formatDuration, formatMoney, formatTime } from "../../utils/format";
import { Piggy } from "../../components/art/Piggy";

export function MoneyCard({
  account,
  symbol = "$",
  big = false,
}: {
  account: AccountView;
  symbol?: string;
  big?: boolean;
}) {
  return (
    <div className="card relative overflow-hidden !bg-piggysoft !ring-piggy/20">
      <IconWallet size={big ? 44 : 30} className="absolute right-4 top-4 text-piggy/50" />
      <p className={`font-bold text-piggy-deep ${big ? "text-lg" : "text-sm"}`}>💰 Piggy bank</p>
      <CountUp
        value={account.money_cents}
        format={(v) => formatMoney(v, symbol)}
        className={`mt-1 block font-extrabold text-ink ${big ? "text-5xl" : "text-3xl"}`}
      />
      <div className="mt-2 flex flex-wrap gap-1.5">
        {account.next_week_interest_cents > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/70 px-3 py-1 text-xs font-bold text-mint-deep">
            <IconSprout size={14} /> next week +
            {formatMoney(account.next_week_interest_cents, symbol)}
          </span>
        )}
        {account.next_year_interest_cents > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/70 px-3 py-1 text-xs font-bold text-mint-deep">
            <IconSprout size={14} /> next year +
            {formatMoney(account.next_year_interest_cents, symbol)} · {account.savings_apr_percent}% APR
          </span>
        )}
        {account.debt_cents > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/70 px-3 py-1 text-xs font-bold text-lav-deep">
            <IconRocket size={14} /> owes {formatMoney(account.debt_cents, symbol)}
          </span>
        )}
      </div>
    </div>
  );
}

export function ScreenCard({ account, big = false }: { account: AccountView; big?: boolean }) {
  return (
    <div className="card relative overflow-hidden !bg-skysoft !ring-sky/20">
      <IconClock size={big ? 44 : 30} className="absolute right-4 top-4 text-sky/60" />
      <p className={`font-bold text-sky-deep ${big ? "text-lg" : "text-sm"}`}>📺 Screen time</p>
      <CountUp
        value={account.screen_seconds}
        format={(v) => formatDuration(v)}
        className={`mt-1 block font-extrabold text-ink ${big ? "text-5xl" : "text-3xl"}`}
      />
      <p className="mt-2 text-xs font-bold text-sky-deep/60">saved up &amp; ready to use</p>
    </div>
  );
}

export function ExchangeStrip({ quote }: { quote: ExchangeQuote }) {
  const better = quote.rate > quote.base_rate;
  const worse = quote.rate < quote.base_rate;
  return (
    <div className="card flex flex-wrap items-center gap-x-6 gap-y-3 !py-4">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-buttersoft text-butter-deep">
          <IconExchange />
        </span>
        <div>
          <p className="text-2xl font-extrabold leading-6">
            {quote.rate}
            <span className="ml-1 text-sm font-bold text-ink/40">min / $1</span>
          </p>
          <p className="text-xs font-bold text-ink/45">
            base {quote.base_rate} min/$1 · {quote.timezone}
          </p>
        </div>
      </div>
      {quote.rule ? (
        <span
          className={`rounded-full px-3 py-1 text-xs font-extrabold ${
            better ? "bg-mintsoft text-mint-deep" : worse ? "bg-red-50 text-red-500" : "bg-piggysoft text-piggy-deep"
          }`}
        >
          {better ? "⭐ off-peak bonus" : worse ? "⏰ peak hours" : "⏱ special rate"}: {quote.rule.name}
        </span>
      ) : (
        <span className="rounded-full bg-piggysoft px-3 py-1 text-xs font-extrabold text-piggy-deep">
          standard rate right now
        </span>
      )}
      <div className="ml-auto flex gap-4 text-xs font-bold text-ink/50">
        {quote.until && (
          <span>
            until <span className="text-ink">{formatTime(quote.until)}</span>
          </span>
        )}
        {quote.next_change && (
          <span>
            then <span className="text-ink">{quote.next_change.rate} min/$</span>
          </span>
        )}
      </div>
    </div>
  );
}

export function ConvertPanel({
  account,
  quote,
  onDone,
  allowAdminNote = false,
}: {
  account: AccountView;
  quote: ExchangeQuote;
  onDone: () => void;
  allowAdminNote?: boolean;
}) {
  const toast = useToast();
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const cents = useMemo(() => {
    const t = amount.trim().replace(/^\$/, "");
    return /^\d+(\.\d{1,2})?$/.test(t) ? Math.round(parseFloat(t) * 100) : 0;
  }, [amount]);
  const minutes = Math.floor((cents * quote.rate * 60) / 100 / 60);

  async function convert() {
    if (!cents) return;
    setBusy(true);
    try {
      const res = await api.post<{ seconds: number }>(`/api/v1/accounts/${account.id}/convert`, {
        amount_cents: cents,
      });
      toast(`Converted to ${Math.floor(res.seconds / 60)} minutes of screen time! 📺✨`);
      setAmount("");
      onDone();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Convert failed", "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <p className="flex items-center gap-2 font-extrabold">
        <IconExchange size={20} className="text-butter-deep" /> Turn money into screen time
      </p>
      <p className="mt-1 text-sm font-bold text-ink/45">
        {quote.rate} minutes for every $1 {quote.rule ? `(${quote.rule.name})` : "(standard rate)"}
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="w-36">
          <label className="label" htmlFor="convert-amount">
            Dollars
          </label>
          <input
            id="convert-amount"
            className="input"
            inputMode="decimal"
            placeholder="e.g. 2.50"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </div>
        <span className="pb-3 text-2xl text-ink/30">→</span>
        <div className="pb-3.5">
          <p className="text-3xl font-extrabold text-sky-deep tabular">
            {minutes > 0 ? `${minutes} min` : "—"}
          </p>
        </div>
        <button className="btn-sky ml-auto" disabled={!cents || busy || cents > account.money_cents} onClick={convert}>
          {busy ? "Converting…" : "Convert 💱"}
        </button>
      </div>
      {cents > account.money_cents && (
        <p className="mt-2 text-xs font-bold text-red-400">That's more than the piggy bank has!</p>
      )}
      {allowAdminNote && (
        <p className="mt-2 text-xs font-bold text-ink/40">Converting for this account as the parent 👑</p>
      )}
    </div>
  );
}

export function LoansCard({
  account,
  loans,
  onChanged,
}: {
  account: AccountView;
  loans: Loan[];
  onChanged: () => void;
}) {
  const toast = useToast();
  const [repay, setRepay] = useState<Record<number, string>>({});
  const [repayNote, setRepayNote] = useState<Record<number, string>>({});
  const active = loans.filter((l) => l.status === "active");

  async function doRepay(loan: Loan) {
    const t = (repay[loan.id] ?? "").trim().replace(/^\$/, "");
    if (!/^\d+(\.\d{1,2})?$/.test(t)) return;
    const cents = Math.round(parseFloat(t) * 100);
    setBusyId(loan.id);
    try {
      await api.post(`/api/v1/loans/${loan.id}/repay`, {
        amount_cents: cents,
        note: (repayNote[loan.id] ?? "").trim(),
      });
      toast(`Repaid $${t} 🙏`);
      setRepay((r) => ({ ...r, [loan.id]: "" }));
      setRepayNote((r) => ({ ...r, [loan.id]: "" }));
      onChanged();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Repay failed", "err");
    } finally {
      setBusyId(null);
    }
  }
  const [busyId, setBusyId] = useState<number | null>(null);

  if (active.length === 0) return null;
  return (
    <div className="card !bg-lavsoft !ring-lav/20">
      <p className="flex items-center gap-2 font-extrabold">
        <IconRocket size={20} className="text-lav-deep" /> My loans
      </p>
      <div className="mt-3 flex flex-col gap-3">
        {active.map((loan) => (
          <div key={loan.id} className="rounded-2xl bg-white/70 p-3">
            <div className="flex flex-wrap items-baseline gap-x-3">
              <p className="text-xl font-extrabold">{formatMoney(loan.outstanding_cents)}</p>
              <span className="text-xs font-bold text-ink/45">
                at {loan.apr_percent}% APR · costs{" "}
                {formatMoney(loan.next_day_interest_cents)}/day
              </span>
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <input
                className="input !w-32 !py-2 text-sm"
                inputMode="decimal"
                placeholder="$ pay back"
                value={repay[loan.id] ?? ""}
                onChange={(e) => setRepay((r) => ({ ...r, [loan.id]: e.target.value }))}
              />
              <input
                className="input !min-w-36 flex-1 !py-2 text-sm"
                placeholder="note (optional)"
                value={repayNote[loan.id] ?? ""}
                onChange={(e) => setRepayNote((r) => ({ ...r, [loan.id]: e.target.value }))}
              />
              <button
                className="btn-mint !py-2 text-sm"
                disabled={busyId === loan.id || account.money_cents <= 0}
                onClick={() => doRepay(loan)}
              >
                Repay
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function BorrowCard({
  account,
  quote,
  onDone,
}: {
  account: AccountView;
  quote: ExchangeQuote;
  onDone: () => void;
}) {
  const toast = useToast();
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const cents = useMemo(() => {
    const t = amount.trim().replace(/^\$/, "");
    return /^\d+(\.\d{1,2})?$/.test(t) ? Math.round(parseFloat(t) * 100) : 0;
  }, [amount]);
  const limitLeft = Math.max(0, (quote.borrow_limit_cents ?? 0) - account.debt_cents);

  async function doBorrow() {
    if (!cents) return;
    setBusy(true);
    try {
      await api.post("/api/v1/loans/borrow", {
        account_id: account.id, amount_cents: cents, note: note.trim(),
      });
      toast(`Borrowed $${amount} — remember it grows every day! 🚀`);
      setAmount("");
      setNote("");
      onDone();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Borrow failed", "err");
    } finally {
      setBusy(false);
    }
  }

  if (!quote.borrow_enabled || !account.can_borrow) return null;
  return (
    <div className="card !bg-lavsoft !ring-lav/20">
      <p className="flex items-center gap-2 font-extrabold">
        <IconRocket size={20} className="text-lav-deep" /> Borrow money
      </p>
      <p className="mt-1 text-sm font-bold text-ink/45">
        {quote.borrow_apr_percent}% APR, added to your debt every day. You can borrow up to{" "}
        {formatMoney(limitLeft)} more.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <input
          className="input !w-28"
          inputMode="decimal"
          placeholder="$ amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <input
          className="input !min-w-36 flex-1"
          placeholder="what's it for? (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button className="btn-mint" disabled={!cents || busy || cents > limitLeft} onClick={doBorrow}>
          {busy ? "Borrowing…" : "Borrow 🚀"}
        </button>
      </div>
    </div>
  );
}

export function ToddlerStickers({ moneyCents }: { moneyCents: number }) {
  const stars = Math.floor(moneyCents / 500);
  const toward = moneyCents % 500;
  return (
    <div className="card flex flex-col items-center gap-3 !bg-buttersoft !ring-butter/30">
      <p className="font-extrabold">My saving stickers ⭐</p>
      <div className="flex min-h-14 flex-wrap items-center justify-center gap-1.5">
        {Array.from({ length: Math.max(stars, 1) }).map((_, i) => (
          <span key={i} className={`text-3xl ${i < stars ? "animate-sparkle" : "opacity-20 grayscale"}`}>
            ⭐
          </span>
        ))}
        {stars === 0 && <span className="text-sm font-bold text-ink/40">save $5 for your first star!</span>}
      </div>
      <p className="text-xs font-bold text-ink/45">
        {stars > 0 ? `$${(toward / 100).toFixed(2)} toward the next star` : "every $5 saved = one shiny star"}
      </p>
    </div>
  );
}

export function PiggyMoodFor(account: AccountView) {
  if (account.money_cents <= 0) return "think" as const;
  if (account.money_cents >= 10000) return "celebrate" as const;
  return "happy" as const;
}

export { Piggy };
