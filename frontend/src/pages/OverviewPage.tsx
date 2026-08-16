import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../api/auth";
import type { Overview } from "../api/types";
import { Badge, Field, Modal, PageLoader, Spinner, useToast } from "../components/ui";
import { formatDuration, formatMoney, parseMoneyToCents } from "../utils/format";
import { IconArrowRight, IconClock, IconPlus, IconWallet } from "../components/art/icons";
import { Piggy } from "../components/art/Piggy";
import { CountUp } from "../components/charts";

/** Admin home: every kid at a glance + quick parent tools. */
export default function OverviewPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [err, setErr] = useState("");
  const toast = useToast();
  const [quick, setQuick] = useState<null | { id: number; name: string; kind: "money" | "time" }>(null);
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api
      .get<Overview>("/api/v1/overview")
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);
  useEffect(load, [load]);

  async function submitQuick() {
    if (!quick) return;
    setBusy(true);
    try {
      if (quick.kind === "money") {
        const cents = parseMoneyToCents(amount);
        if (!cents) throw new Error("Enter a valid dollar amount");
        await api.post(`/api/v1/accounts/${quick.id}/deposit`, { amount_cents: cents, note });
        toast(`Deposited $${amount} to ${quick.name} 💰`);
      } else {
        const secs = Math.round(parseFloat(amount) * 60);
        if (!Number.isFinite(secs) || secs <= 0) throw new Error("Enter minutes");
        await api.post(`/api/v1/accounts/${quick.id}/grant-time`, { amount_seconds: secs, note });
        toast(`Granted ${amount} minutes to ${quick.name} ⏰`);
      }
      setQuick(null);
      setAmount("");
      setNote("");
      load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "err");
    } finally {
      setBusy(false);
    }
  }

  if (!user || user.role !== "admin") return <Navigate to="/" replace />;
  if (err) return <div className="card mt-8 text-center font-bold text-red-400">{err}</div>;
  if (!data) return <PageLoader />;

  const kids = data.accounts;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title">The family bank 🏦</h1>
          <p className="text-sm font-bold text-ink/45">{kids.length} account{kids.length === 1 ? "" : "s"} · click a kid for details</p>
        </div>
        <Piggy mood="happy" size={90} className="hidden sm:block" />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card !bg-piggysoft !ring-piggy/20 text-center">
          <p className="text-xs font-extrabold uppercase tracking-wide text-piggy-deep">total savings</p>
          <CountUp
            value={data.totals.money_cents}
            format={(v) => formatMoney(v)}
            className="text-3xl font-extrabold"
          />
        </div>
        <div className="card !bg-skysoft !ring-sky/20 text-center">
          <p className="text-xs font-extrabold uppercase tracking-wide text-sky-deep">total screen time</p>
          <CountUp
            value={data.totals.screen_seconds}
            format={(v) => formatDuration(v)}
            className="text-3xl font-extrabold"
          />
        </div>
        <div className="card !bg-lavsoft !ring-lav/20 text-center">
          <p className="text-xs font-extrabold uppercase tracking-wide text-lav-deep">total debt</p>
          <CountUp
            value={data.totals.debt_cents}
            format={(v) => formatMoney(v)}
            className="text-3xl font-extrabold"
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {kids.map((a) => (
          <div key={a.id} className="card group relative flex flex-col gap-3 transition-transform hover:-translate-y-0.5">
            <Link to={`/account/${a.id}`} className="flex items-center gap-3">
              <span className="grid h-14 w-14 place-items-center rounded-3xl bg-piggysoft text-3xl shadow-soft">
                {a.avatar}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-lg font-extrabold">{a.display_name}</p>
                <p className="text-xs font-bold text-ink/40">@{a.username}</p>
              </div>
              <IconArrowRight size={18} className="text-ink/20 group-hover:text-piggy" />
            </Link>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-2xl bg-piggysoft/70 px-3 py-2">
                <p className="flex items-center gap-1 text-[11px] font-extrabold text-piggy-deep">
                  <IconWallet size={13} /> money
                </p>
                <p className="text-xl font-extrabold tabular">{formatMoney(a.money_cents)}</p>
              </div>
              <div className="rounded-2xl bg-skysoft/70 px-3 py-2">
                <p className="flex items-center gap-1 text-[11px] font-extrabold text-sky-deep">
                  <IconClock size={13} /> time
                </p>
                <p className="text-xl font-extrabold tabular">{formatDuration(a.screen_seconds)}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge tone={a.ui_mode === "teen" ? "lav" : a.ui_mode === "kid" ? "mint" : "butter"}>
                {a.ui_mode}
              </Badge>
              {a.debt_cents > 0 && <Badge tone="red">owes {formatMoney(a.debt_cents)}</Badge>}
              {!a.can_convert && <Badge tone="sky">no convert</Badge>}
              {a.can_borrow && <Badge tone="lav">can borrow</Badge>}
            </div>
            <div className="mt-auto flex gap-2">
              <button
                className="btn-ghost flex-1 !py-2 text-xs"
                onClick={() => setQuick({ id: a.id, name: a.display_name, kind: "money" })}
              >
                <IconPlus size={14} /> money
              </button>
              <button
                className="btn-ghost flex-1 !py-2 text-xs"
                onClick={() => setQuick({ id: a.id, name: a.display_name, kind: "time" })}
              >
                <IconPlus size={14} /> time
              </button>
            </div>
          </div>
        ))}
      </div>

      <Modal
        open={quick !== null}
        onClose={() => setQuick(null)}
        title={quick?.kind === "money" ? `💰 Deposit to ${quick?.name}` : `⏰ Grant time to ${quick?.name}`}
      >
        <div className="flex flex-col gap-4">
          <Field label={quick?.kind === "money" ? "Amount ($)" : "Minutes"}>
            <input
              className="input"
              inputMode="decimal"
              placeholder={quick?.kind === "money" ? "e.g. 20" : "e.g. 45"}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </Field>
          <Field label="Note (optional)">
            <input
              className="input"
              placeholder="allowance, birthday…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          <div className="flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setQuick(null)}>
              Cancel
            </button>
            <button className="btn-primary" disabled={busy} onClick={submitQuick}>
              {busy ? <Spinner className="h-4 w-4" /> : null} Confirm
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
