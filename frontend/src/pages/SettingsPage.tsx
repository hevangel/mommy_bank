import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ExchangeRule, Settings } from "../api/types";
import { Badge, Field, PageLoader, Toggle, useToast } from "../components/ui";
import { DAY_NAMES, minuteOfDayToHM } from "../utils/format";
import { IconPencil, IconPlus, IconSettings, IconTrash } from "../components/art/icons";
import { Modal } from "../components/ui";
import { IconExchange } from "../components/art/icons";

export default function SettingsPage() {
  const toast = useToast();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [rules, setRules] = useState<ExchangeRule[]>([]);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get<Settings>("/api/v1/settings").then(setSettings).catch(() => {});
    api.get<ExchangeRule[]>("/api/v1/exchange-rules").then(setRules).catch(() => {});
  }, []);
  useEffect(load, [load]);

  async function save(key: keyof Settings, value: string | number | boolean) {
    if (!settings) return;
    setSavingKey(key);
    try {
      const next = await api.patch<Partial<Settings>>("/api/v1/settings", { [key]: value });
      setSettings((s) => ({ ...(s as Settings), ...next }));
      toast(`${key} saved ✅`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Save failed", "err");
    } finally {
      setSavingKey(null);
    }
  }

  if (!settings) return <PageLoader />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="page-title flex items-center gap-2">
          <IconSettings /> Bank rules
        </h1>
        <p className="text-sm font-bold text-ink/45">interest, borrowing and the money→time exchange</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Interest */}
        <div className="card flex flex-col gap-4">
          <p className="font-extrabold">🌱 Savings interest</p>
          <Toggle
            checked={settings.interest_enabled}
            onChange={(v) => save("interest_enabled", v)}
            label="Pay interest on savings"
          />
          <NumberRow
            label="Interest rate (% APR, compounded daily)"
            value={settings.savings_apr_percent}
            disabled={!settings.interest_enabled}
            saving={savingKey === "savings_apr_percent"}
            onSave={(v) => save("savings_apr_percent", v)}
          />
          <p className="text-xs font-bold text-ink/40">
            $100 grows to ~${(100 * (1 + settings.savings_apr_percent / 100 / 365) ** 365).toFixed(2)} in a year.
          </p>
        </div>

        {/* Borrowing */}
        <div className="card flex flex-col gap-4">
          <p className="font-extrabold">🚀 Borrowing</p>
          <Toggle
            checked={settings.borrow_enabled}
            onChange={(v) => save("borrow_enabled", v)}
            label="Allow kids to borrow (loan feature)"
          />
          <NumberRow
            label="Loan rate (% APR, compounded daily)"
            value={settings.borrow_apr_percent}
            disabled={!settings.borrow_enabled}
            saving={savingKey === "borrow_apr_percent"}
            onSave={(v) => save("borrow_apr_percent", v)}
          />
          <NumberRow
            label="Debt cap (cents, e.g. 5000 = $50)"
            value={settings.borrow_limit_cents}
            disabled={!settings.borrow_enabled}
            saving={savingKey === "borrow_limit_cents"}
            onSave={(v) => save("borrow_limit_cents", v)}
          />
          <p className="text-xs font-bold text-ink/40">
            Kids also need "can borrow" turned on in the Family page.
          </p>
        </div>

        {/* Exchange */}
        <div className="card flex flex-col gap-4">
          <p className="font-extrabold">💱 Money → screen time</p>
          <NumberRow
            label="Base rate (minutes per $1)"
            value={settings.exchange_base_minutes_per_dollar}
            saving={savingKey === "exchange_base_minutes_per_dollar"}
            onSave={(v) => save("exchange_base_minutes_per_dollar", v)}
          />
          <NumberRow
            label="Minimum conversion (cents)"
            value={settings.min_convert_cents}
            saving={savingKey === "min_convert_cents"}
            onSave={(v) => save("min_convert_cents", v)}
          />
          <Field label="Currency symbol">
            <input
              className="input !w-24"
              defaultValue={settings.currency_symbol}
              onBlur={(e) => {
                const v = e.target.value.trim();
                if (v && v !== settings.currency_symbol) save("currency_symbol", v);
              }}
            />
          </Field>
          <Field label="Timezone (for peak/off-peak windows)" hint="IANA name, e.g. America/Los_Angeles or Asia/Hong_Kong">
            <input
              className="input"
              defaultValue={settings.timezone}
              onBlur={(e) => {
                const v = e.target.value.trim();
                if (v && v !== settings.timezone) save("timezone", v);
              }}
            />
          </Field>
        </div>
      </div>

      <RulesEditor rules={rules} onChanged={load} />
    </div>
  );
}

function NumberRow({
  label,
  value,
  disabled,
  saving,
  onSave,
}: {
  label: string;
  value: number;
  disabled?: boolean;
  saving?: boolean;
  onSave: (v: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const num = parseFloat(draft);
  const valid = Number.isFinite(num) && num >= 0;
  return (
    <div className={disabled ? "opacity-40" : ""}>
      <label className="label">{label}</label>
      <div className="flex gap-2">
        <input
          className="input"
          inputMode="decimal"
          value={draft}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button
          className="btn-ghost shrink-0 !py-2 text-sm"
          disabled={disabled || !valid || saving || num === value}
          onClick={() => onSave(num)}
        >
          {saving ? "…" : "save"}
        </button>
      </div>
    </div>
  );
}

function RulesEditor({ rules, onChanged }: { rules: ExchangeRule[]; onChanged: () => void }) {
  const toast = useToast();
  const [editing, setEditing] = useState<ExchangeRule | "new" | null>(null);

  async function remove(rule: ExchangeRule) {
    if (!window.confirm(`Delete rule "${rule.name}"?`)) return;
    try {
      await api.del(`/api/v1/exchange-rules/${rule.id}`);
      toast(`Deleted "${rule.name}" 🗑️`);
      onChanged();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Delete failed", "err");
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 font-extrabold">
          <IconExchange size={20} className="text-butter-deep" /> Peak &amp; off-peak rate rules
        </p>
        <button className="btn-ghost !py-2 text-sm" onClick={() => setEditing("new")}>
          <IconPlus size={16} /> add rule
        </button>
      </div>
      <p className="mt-1 text-xs font-bold text-ink/40">
        Windows match in the bank's timezone; the lowest priority number wins; end is exclusive; end before start crosses midnight.
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {rules.length === 0 && (
          <p className="py-6 text-center text-sm font-bold text-ink/35">
            no rules — the base rate always applies
          </p>
        )}
        {rules.map((r) => (
          <div key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-2xl bg-cream px-4 py-3">
            <p className="font-extrabold">{r.name}</p>
            <Badge tone={r.minutes_per_dollar >= 10 ? "mint" : "red"}>
              {r.minutes_per_dollar} min/$
            </Badge>
            <span className="text-xs font-bold text-ink/50">
              {r.days.length === 7
                ? "every day"
                : r.days.map((d) => DAY_NAMES[d]).join(",")}{" "}
              · {minuteOfDayToHM(r.start_minute)}–{r.end_minute === 1440 ? "24:00" : minuteOfDayToHM(r.end_minute)}
            </span>
            <Badge tone="sky">prio {r.priority}</Badge>
            {!r.is_active && <Badge tone="red">off</Badge>}
            <span className="ml-auto flex gap-1">
              <button
                className="rounded-xl p-2 text-ink/40 hover:bg-piggysoft hover:text-ink"
                onClick={() => setEditing(r)}
                aria-label={`edit ${r.name}`}
              >
                <IconPencil size={17} />
              </button>
              <button
                className="rounded-xl p-2 text-ink/40 hover:bg-red-50 hover:text-red-500"
                onClick={() => remove(r)}
                aria-label={`delete ${r.name}`}
              >
                <IconTrash size={17} />
              </button>
            </span>
          </div>
        ))}
      </div>
      {editing && <RuleForm rule={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={onChanged} />}
    </div>
  );
}

function RuleForm({
  rule,
  onClose,
  onSaved,
}: {
  rule: ExchangeRule | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [name, setName] = useState(rule?.name ?? "");
  const [days, setDays] = useState<number[]>(rule?.days ?? [0, 1, 2, 3, 4, 5, 6]);
  const [start, setStart] = useState(minuteOfDayToHM(rule?.start_minute ?? 0));
  const [end, setEnd] = useState(minuteOfDayToHM(rule?.end_minute === 1440 ? 1439 : (rule?.end_minute ?? 1439)));
  const [rate, setRate] = useState(String(rule?.minutes_per_dollar ?? 10));
  const [priority, setPriority] = useState(String(rule?.priority ?? 100));
  const [active, setActive] = useState(rule?.is_active ?? true);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const [sh, sm] = start.split(":").map(Number);
      const [eh, em] = end.split(":").map(Number);
      const body = {
        name,
        days,
        start_minute: sh * 60 + sm,
        end_minute: eh * 60 + em,
        minutes_per_dollar: parseFloat(rate),
        priority: parseInt(priority, 10) || 100,
        is_active: active,
      };
      if (!body.name) throw new Error("Give the rule a name");
      if (!Number.isFinite(body.minutes_per_dollar) || body.minutes_per_dollar <= 0) throw new Error("Rate must be > 0");
      if (!days.length) throw new Error("Pick at least one day");
      if (rule) {
        await api.patch(`/api/v1/exchange-rules/${rule.id}`, body);
        toast("Rule updated ✅");
      } else {
        await api.post("/api/v1/exchange-rules", body);
        toast("Rule added ✅");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Save failed", "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={rule ? `Edit "${rule.name}"` : "New exchange rule"}>
      <div className="flex flex-col gap-4">
        <Field label="Name">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Bedtime peak" />
        </Field>
        <Field label="Days">
          <div className="flex flex-wrap gap-1.5">
            {DAY_NAMES.map((d, i) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays((old) => (old.includes(i) ? old.filter((x) => x !== i) : [...old, i].sort()))}
                className={`rounded-xl px-3 py-1.5 text-sm font-bold ${days.includes(i) ? "bg-mint text-white" : "bg-cream text-ink/45"}`}
              >
                {d}
              </button>
            ))}
          </div>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Start (local time)">
            <input type="time" className="input" value={start} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field label="End (exclusive)">
            <input type="time" className="input" value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Rate (minutes per $1)">
            <input className="input" inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value)} />
          </Field>
          <Field label="Priority (lower wins)">
            <input className="input" inputMode="numeric" value={priority} onChange={(e) => setPriority(e.target.value)} />
          </Field>
        </div>
        <Toggle checked={active} onChange={setActive} label="Rule active" />
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={busy} onClick={save}>
            {busy ? "…" : rule ? "Save rule" : "Add rule"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
