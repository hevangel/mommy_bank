import { useAuth } from "../../api/auth";
import type { AccountView } from "../../api/types";
import { CountUp } from "../../components/charts";
import { Piggy } from "../../components/art/Piggy";
import { formatClock, formatMoney } from "../../utils/format";
import { ToddlerStickers } from "./shared";
import { IconClock } from "../../components/art/icons";

/** Pre-schooler: picture book. Read-only, giant numbers, zero jargon. */
export default function ToddlerDashboard({ account }: { account: AccountView }) {
  const { user } = useAuth();
  return (
    <div className="flex flex-col items-center gap-6 py-4">
      <div className="flex items-center gap-3">
        <span className="text-5xl">{account.avatar}</span>
        <h1 className="text-3xl font-extrabold">{user?.display_name}</h1>
      </div>

      <Piggy mood={account.money_cents > 0 ? "celebrate" : "think"} size={210} />

      <div className="w-full max-w-md rounded-[2.5rem] bg-piggysoft p-8 text-center shadow-chunky ring-4 ring-white">
        <p className="text-xl font-extrabold text-piggy-deep">My money</p>
        <CountUp
          value={account.money_cents}
          format={(v) => formatMoney(v)}
          className="block text-6xl font-extrabold text-ink"
        />
        <p className="mt-1 text-sm font-bold text-ink/40">in my piggy 🐷</p>
      </div>

      <div className="w-full max-w-md rounded-[2.5rem] bg-skysoft p-8 text-center shadow-chunky ring-4 ring-white">
        <IconClock size={40} className="mx-auto text-sky-deep" />
        <p className="mt-1 text-xl font-extrabold text-sky-deep">My TV time</p>
        <CountUp
          value={account.screen_seconds}
          format={(v) => formatClock(v)}
          className="block text-6xl font-extrabold text-ink"
        />
        <p className="mt-1 text-sm font-bold text-ink/40">hours : minutes</p>
      </div>

      <ToddlerStickers moneyCents={account.money_cents} />

      <p className="rounded-full bg-white px-6 py-3 text-center text-lg font-extrabold text-piggy-deep shadow-soft">
        Ask Mommy or Daddy to add more! 💕
      </p>
    </div>
  );
}
