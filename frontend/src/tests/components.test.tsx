import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "../pages/LoginPage";
import type { AccountView, User } from "../api/types";
import { MoneyCard, ScreenCard, ExchangeStrip, ConvertPanel } from "../pages/dashboard/shared";
import ToddlerDashboard from "../pages/dashboard/ToddlerDashboard";
import { formatDuration } from "../utils/format";

vi.mock("../api/client", async (importOriginal) => {
  const orig = await importOriginal<typeof import("../api/client")>();
  return { ...orig, api: { ...orig.api, get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() } };
});

const authState: {
  user: User | null;
  account: AccountView | null;
  loading: boolean;
  login: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  refresh: ReturnType<typeof vi.fn>;
} = { user: null, account: null, loading: false, login: vi.fn(), logout: vi.fn(), refresh: vi.fn() };

vi.mock("../api/auth", () => ({ useAuth: () => authState }));

const acct = (over: Partial<AccountView> = {}): AccountView => ({
  id: 1,
  user_id: 2,
  username: "teen",
  display_name: "Big Bro",
  avatar: "🧑‍🚀",
  ui_mode: "teen",
  can_convert: true,
  can_borrow: false,
  money_cents: 12345,
  screen_seconds: 7500,
  last_interest_at: "2026-08-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  next_day_interest_cents: 2,
  next_week_interest_cents: 16,
  next_year_interest_cents: 852,
  savings_apr_percent: 6.7,
  debt_cents: 0,
  active_loans: 0,
  ...over,
});

const toddlerUser: User = {
  id: 2,
  username: "toddler",
  display_name: "Tiny Tot",
  role: "user",
  ui_mode: "toddler",
  avatar: "🐻",
  email: null,
  can_convert: false,
  can_borrow: false,
  is_active: true,
  created_at: "",
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.user = null;
  });

  it("renders the mascot and form", () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
  });

  it("shows an error on failed login", async () => {
    authState.login.mockRejectedValueOnce(new Error("Wrong username or password"));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText(/username/i), "kid");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/wrong username or password/i);
  });
});

describe("balance cards", () => {
  it("shows money with next week and next year interest", () => {
    render(<MoneyCard account={acct()} />);
    expect(screen.getByText("$123.45")).toBeInTheDocument();
    expect(screen.getByText(/next week/)).toBeInTheDocument();
    expect(screen.getByText(/next year/)).toBeInTheDocument();
    expect(screen.queryByText(/tomorrow/)).not.toBeInTheDocument();
  });

  it("shows debt badge when kid owes money", () => {
    render(<MoneyCard account={acct({ debt_cents: 500 })} />);
    expect(screen.getByText(/owes \$5\.00/)).toBeInTheDocument();
  });

  it("shows screen time", () => {
    render(<ScreenCard account={acct()} />);
    expect(screen.getByText(formatDuration(7500))).toBeInTheDocument();
  });
});

describe("ExchangeStrip", () => {
  const baseQuote = {
    base_rate: 10,
    until: "2026-08-16T22:00:00Z",
    next_change: { at: "2026-08-16T22:00:00Z", rate: 10 },
    local_time: "2026-08-16T20:00:00Z",
    timezone: "UTC",
  };

  it("shows the active peak rule and rate", () => {
    render(
      <ExchangeStrip
        quote={{ ...baseQuote, rate: 7, rule: { id: 1, name: "Bedtime peak", minutes_per_dollar: 7 } }}
      />,
    );
    expect(screen.getByText(/bedtime peak/i)).toBeInTheDocument();
    expect(screen.getByText(/peak hours/i)).toBeInTheDocument();
  });

  it("marks bonus rates as off-peak", () => {
    render(
      <ExchangeStrip
        quote={{
          ...baseQuote,
          rate: 15,
          rule: { id: 2, name: "Weekend morning bonus", minutes_per_dollar: 15 },
          until: null,
          next_change: null,
        }}
      />,
    );
    expect(screen.getByText(/off-peak bonus/i)).toBeInTheDocument();
  });
});

describe("ConvertPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("previews minutes before converting", async () => {
    const { api } = await import("../api/client");
    vi.mocked(api.post).mockResolvedValueOnce({ seconds: 1200 });
    const onDone = vi.fn();
    render(
      <ConvertPanel
        account={acct()}
        quote={{
          rate: 12,
          base_rate: 10,
          rule: { id: 1, name: "After-school", minutes_per_dollar: 12 },
          until: null,
          next_change: null,
          local_time: "",
          timezone: "UTC",
        }}
        onDone={onDone}
      />,
    );
    await userEvent.type(screen.getByLabelText(/dollars/i), "2");
    expect(screen.getByText("24 min")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /convert/i }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(onDone).toHaveBeenCalled();
  });

  it("refuses to convert more than the balance", async () => {
    render(
      <ConvertPanel
        account={acct({ money_cents: 100 })}
        quote={{
          rate: 10,
          base_rate: 10,
          rule: null,
          until: null,
          next_change: null,
          local_time: "",
          timezone: "UTC",
        }}
        onDone={() => {}}
      />,
    );
    await userEvent.type(screen.getByLabelText(/dollars/i), "5");
    const btn = screen.getByRole("button", { name: /convert/i });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/more than the piggy bank/i)).toBeInTheDocument();
  });
});

describe("ToddlerDashboard", () => {
  it("renders giant read-only balances and stickers", () => {
    authState.user = toddlerUser;
    render(
      <MemoryRouter>
        <ToddlerDashboard
          account={acct({
            money_cents: 1250,
            screen_seconds: 1800,
            display_name: "Tiny Tot",
            avatar: "🐻",
            ui_mode: "toddler",
          })}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("$12.50")).toBeInTheDocument();
    expect(screen.getByText("0:30")).toBeInTheDocument();
    expect(screen.getByText(/ask mommy or daddy/i)).toBeInTheDocument();
    expect(screen.getByText(/saving stickers/i)).toBeInTheDocument();
  });
});
