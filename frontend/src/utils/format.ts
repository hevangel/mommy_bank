/** Formatting helpers — money (cents) and screen time (seconds). */

export function formatMoney(cents: number, symbol = "$"): string {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  return `${sign}${symbol}${Math.floor(abs / 100).toLocaleString("en-US")}.${String(abs % 100).padStart(2, "0")}`;
}

export function parseMoneyToCents(text: string): number | null {
  const t = text.trim().replace(/^\$/, "");
  if (!/^\d+(\.\d{1,2})?$/.test(t)) return null;
  const cents = Math.round(parseFloat(t) * 100);
  return Number.isFinite(cents) && cents > 0 ? cents : null;
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${String(m % 60).padStart(2, "0")}m`;
  return `${m}m`;
}

export function formatMinutes(seconds: number): string {
  return `${Math.floor(seconds / 60)} min`;
}

export function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const h = Math.floor(m / 60);
  return `${h}:${String(m % 60).padStart(2, "0")}`;
}

export function formatSignedMoney(cents: number, symbol = "$"): string {
  return cents > 0 ? `+${formatMoney(cents, symbol)}` : formatMoney(cents, symbol);
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function minuteOfDayToHM(minute: number): string {
  const h = Math.floor(minute / 60);
  const m = minute % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function hmToMinuteOfDay(hm: string): number | null {
  const match = /^(\d{1,2}):(\d{2})$/.test(hm.trim()) ? hm.trim().match(/^(\d{1,2}):(\d{2})$/) : null;
  if (!match) return null;
  const h = parseInt(match[1], 10);
  const mm = parseInt(match[2], 10);
  if (h > 23 || mm > 59) return null;
  return h * 60 + mm;
}

export const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function kindEmoji(kind: string): string {
  switch (kind) {
    case "deposit":
      return "💰";
    case "withdraw":
      return "🛍️";
    case "interest":
      return "🌱";
    case "borrow":
      return "🚀";
    case "repay":
      return "🙏";
    case "loan_interest":
      return "📉";
    case "convert_out":
      return "💱";
    case "convert_in":
      return "📺";
    case "grant":
      return "⏰";
    case "deduct":
      return "⌛";
    case "adjust":
      return "✏️";
    default:
      return "•";
  }
}

export function kindLabel(kind: string): string {
  const map: Record<string, string> = {
    deposit: "Deposit",
    withdraw: "Withdraw",
    interest: "Interest",
    borrow: "Borrowed",
    repay: "Repaid",
    loan_interest: "Loan interest",
    convert_out: "Money → time",
    convert_in: "Screen time from money",
    grant: "Time granted",
    deduct: "Time deducted",
    adjust: "Correction",
  };
  return map[kind] ?? kind;
}
