export type Role = "admin" | "user";
export type UiMode = "teen" | "kid" | "toddler";
export type Ledger = "money" | "screen" | "debt";

export interface User {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  ui_mode: UiMode;
  avatar: string;
  email: string | null;
  can_convert: boolean;
  can_borrow: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AccountView {
  id: number;
  user_id: number;
  username: string;
  display_name: string;
  avatar: string;
  ui_mode: UiMode;
  can_convert: boolean;
  can_borrow: boolean;
  money_cents: number;
  screen_seconds: number;
  last_interest_at: string;
  created_at: string;
  next_day_interest_cents: number;
  savings_apr_percent: number;
  debt_cents: number;
  active_loans: number;
}

export interface Transaction {
  id: number;
  account_id: number;
  ledger: Ledger;
  kind: string;
  delta: number;
  balance_after: number;
  note: string;
  meta: Record<string, unknown>;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
}

export interface Loan {
  id: number;
  account_id: number;
  username: string;
  principal_cents: number;
  outstanding_cents: number;
  apr_percent: number;
  status: "active" | "repaid";
  created_at: string;
  repaid_at: string | null;
  next_day_interest_cents: number;
}

export interface ExchangeQuote {
  rate: number;
  base_rate: number;
  rule: { id: number; name: string; minutes_per_dollar: number } | null;
  until: string | null;
  next_change: { at: string; rate: number } | null;
  local_time: string;
  timezone: string;
  borrow_enabled?: boolean;
  borrow_apr_percent?: number;
  borrow_limit_cents?: number;
}

export interface ExchangeRule {
  id: number;
  name: string;
  priority: number;
  days: number[];
  start_minute: number;
  end_minute: number;
  minutes_per_dollar: number;
  is_active: boolean;
}

export interface Settings {
  savings_apr_percent: number;
  interest_enabled: boolean;
  borrow_enabled: boolean;
  borrow_apr_percent: number;
  borrow_limit_cents: number;
  exchange_base_minutes_per_dollar: number;
  min_convert_cents: number;
  currency_symbol: string;
  timezone: string;
}

export interface Overview {
  accounts: AccountView[];
  totals: { money_cents: number; screen_seconds: number; debt_cents: number };
}
