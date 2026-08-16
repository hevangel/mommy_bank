import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../api/auth";
import type { AccountView, Transaction } from "../api/types";
import { Badge, Field, Modal, PageLoader, Spinner, useToast } from "../components/ui";
import { MoneyCard, ScreenCard } from "./dashboard/shared";
import { formatDateTime, formatDuration, formatMoney, kindEmoji, kindLabel, parseMoneyToCents } from "../utils/format";
import { IconArrowRight, IconMinus, IconPlus } from "../components/art/icons";

type Ledger = "money" | "screen" | "debt";

export default function AccountPage() {
  const { id } = useParams();
  const { user, account: own } = useAuth();
  const [account, setAccount] = useState<AccountView | null>(null);
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [ledger, setLedger] = useState<Ledger>("money");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const accountId = id ?? own?.id;
  const isAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    if (!accountId) return;
    setLoading(true);
    try {
      const [acct, rows] = await Promise.all([
        api.get<AccountView>(`/api/v1/accounts/${accountId}`),
        api.get<Transaction[]>(`/api/v1/accounts/${accountId}/transactions?limit=100&ledger=${ledger}`),
      ]);
      setAccount(acct);
      setTxs(rows);
      setErr("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [accountId, ledger]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !account) return <PageLoader />;
  if (err)
    return (
      <div className="card mt-8 text-center font-bold text-red-400">
        {err}
        <div className="mt-3">
          <Link to="/overview" className="btn-ghost">
            back to kids
          </Link>
        </div>
      </div>
    );
  if (!account) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="page-title flex items-center gap-3">
          <span className="text-4xl">{account.avatar}</span> {account.display_name}
        </h1>
        <div className="flex items-center gap-2">
          <Badge tone={account.ui_mode === "teen" ? "lav" : account.ui_mode === "kid" ? "mint" : "butter"}>
            {account.ui_mode} mode
          </Badge>
          {isAdmin && (
            <Link to={`/account/${account.id}`} className="hidden" aria-hidden />
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <MoneyCard account={account} />
        <ScreenCard account={account} />
      </div>

      {isAdmin && <AdminActions accountId={account.id} onDone={load} />}

      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="font-extrabold">Ledger</p>
          <div className="flex rounded-2xl bg-cream p-1">
            {(["money", "screen", "debt"] as Ledger[]).map((l) => (
              <button
                key={l}
                onClick={() => setLedger(l)}
                className={`rounded-xl px-3.5 py-1.5 text-sm font-bold transition-colors ${
                  ledger === l ? "bg-white text-ink shadow-soft" : "text-ink/45"
                }`}
              >
                {l === "money" ? "💰 money" : l === "screen" ? "📺 time" : "🚀 debt"}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-bold text-ink/40">
                <th className="pb-2 pr-3">when</th>
                <th className="pb-2 pr-3">what</th>
                <th className="pb-2 pr-3">by</th>
                <th className="pb-2 pr-3 text-right">amount</th>
                <th className="pb-2 text-right">balance after</th>
              </tr>
            </thead>
            <tbody>
              {txs.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center font-bold text-ink/35">
                    nothing here yet 🐷
                  </td>
                </tr>
              )}
              {txs.map((t) => (
                <tr key={t.id} className="border-t border-ink/5">
                  <td className="py-2.5 pr-3 font-bold text-ink/50">{formatDateTime(t.created_at)}</td>
                  <td className="py-2.5 pr-3 font-bold">
                    <span className="mr-1.5">{kindEmoji(t.kind)}</span>
                    {kindLabel(t.kind)}
                    {t.note && <span className="ml-1.5 font-normal text-ink/40">{t.note}</span>}
                  </td>
                  <td className="py-2.5 pr-3 text-xs font-bold text-ink/40">
                    {t.created_by_name ?? (t.created_by === null ? "🏦 bank" : "—")}
                  </td>
                  <td
                    className={`py-2.5 pr-3 text-right font-extrabold tabular ${
                      t.delta >= 0 ? "text-mint-deep" : "text-red-400"
                    }`}
                  >
                    {t.ledger === "screen"
                      ? `${t.delta >= 0 ? "+" : "-"}${formatDuration(Math.abs(t.delta))}`
                      : `${t.delta >= 0 ? "+" : ""}${formatMoney(t.delta)}`}
                  </td>
                  <td className="py-2.5 text-right font-bold text-ink/60 tabular">
                    {t.ledger === "screen" ? formatDuration(t.balance_after) : formatMoney(t.balance_after)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/** Admin-only quick actions on any account page. */
function AdminActions({ accountId, onDone }: { accountId: number; onDone: () => void }) {
  const toast = useToast();
  const [open, setOpen] = useState<null | "deposit" | "withdraw" | "grant" | "deduct" | "adjust">(null);
  const [amount, setAmount] = useState("");
  const [minutes, setMinutes] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!open) return;
    setBusy(true);
    try {
      if (open === "deposit" || open === "withdraw") {
        const cents = parseMoneyToCents(amount);
        if (!cents) throw new Error("Enter a valid dollar amount");
        await api.post(`/api/v1/accounts/${accountId}/${open}`, { amount_cents: cents, note });
        toast(`${open === "deposit" ? "Deposited" : "Withdrew"} $${amount} ✅`);
      } else if (open === "grant" || open === "deduct") {
        const secs = Math.round(parseFloat(minutes) * 60);
        if (!Number.isFinite(secs) || secs <= 0) throw new Error("Enter minutes");
        await api.post(`/api/v1/accounts/${accountId}/${open}-time`, { amount_seconds: secs, note });
        toast(`${open === "grant" ? "Granted" : "Deducted"} ${minutes} minutes ⏰`);
      } else if (open === "adjust") {
        const v = parseInt(amount, 10);
        if (!Number.isFinite(v) || v === 0) throw new Error("Enter cents (can be negative)");
        await api.post(`/api/v1/accounts/${accountId}/adjust`, { ledger: "money", amount: v, note });
        toast("Balance corrected ✏️");
      }
      setOpen(null);
      setAmount("");
      setMinutes("");
      setNote("");
      onDone();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "err");
    } finally {
      setBusy(false);
    }
  }

  const title =
    open === "deposit"
      ? "💰 Deposit money"
      : open === "withdraw"
        ? "🛍️ Withdraw money"
        : open === "grant"
          ? "⏰ Grant screen time"
          : open === "deduct"
            ? "⌛ Deduct screen time"
            : "✏️ Correct balance";

  return (
    <div className="card flex flex-wrap items-center gap-2 !bg-piggysoft/60 !ring-piggy/15">
      <p className="mr-2 font-extrabold">Parent tools 👑</p>
      <button className="btn-ghost !py-2 text-sm" onClick={() => setOpen("deposit")}>
        <IconPlus size={16} /> money
      </button>
      <button className="btn-ghost !py-2 text-sm" onClick={() => setOpen("withdraw")}>
        <IconMinus size={16} /> money
      </button>
      <button className="btn-ghost !py-2 text-sm" onClick={() => setOpen("grant")}>
        <IconPlus size={16} /> time
      </button>
      <button className="btn-ghost !py-2 text-sm" onClick={() => setOpen("deduct")}>
        <IconMinus size={16} /> time
      </button>
      <button className="btn-ghost !py-2 text-sm" onClick={() => setOpen("adjust")}>
        ✏️ correct
      </button>

      <Modal open={open !== null} onClose={() => setOpen(null)} title={title}>
        <div className="flex flex-col gap-4">
          {(open === "deposit" || open === "withdraw" || open === "adjust") && (
            <Field label={open === "adjust" ? "Amount in cents (signed, e.g. -50)" : "Amount ($)"}>
              <input
                className="input"
                inputMode="decimal"
                placeholder={open === "adjust" ? "e.g. -50" : "e.g. 12.50"}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </Field>
          )}
          {(open === "grant" || open === "deduct") && (
            <Field label="Minutes">
              <input
                className="input"
                inputMode="numeric"
                placeholder="e.g. 30"
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
              />
            </Field>
          )}
          <Field label="Note (optional)">
            <input
              className="input"
              placeholder="weekly allowance, screen reward…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setOpen(null)}>
              Cancel
            </button>
            <button className="btn-primary" disabled={busy} onClick={submit}>
              {busy ? <Spinner className="h-4 w-4" /> : <IconArrowRight size={18} />} Confirm
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
