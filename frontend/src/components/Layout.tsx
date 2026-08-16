import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../api/auth";
import { PigFace } from "./art/Piggy";
import {
  IconBank,
  IconHome,
  IconLogout,
  IconSettings,
  IconUsers,
  IconChart,
} from "./art/icons";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";

  const nav = isAdmin
    ? [
        { to: "/overview", label: "Kids", icon: <IconUsers size={22} /> },
        { to: "/users", label: "Family", icon: <IconHome size={22} /> },
        { to: "/settings", label: "Bank rules", icon: <IconSettings size={22} /> },
      ]
    : [
        { to: "/", label: "My bank", icon: <IconBank size={22} />, end: true },
        { to: "/account", label: "History", icon: <IconChart size={22} /> },
      ];

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-2xl px-4 py-3 font-bold transition-colors ${
      isActive ? "bg-piggy text-white shadow-pop" : "text-ink/60 hover:bg-piggysoft hover:text-ink"
    }`;

  return (
    <div className="min-h-screen">
      {/* Sidebar (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-ink/5 bg-white/80 backdrop-blur lg:flex">
        <button className="flex items-center gap-2.5 px-5 py-6 text-left" onClick={() => navigate(isAdmin ? "/overview" : "/")}>
          <PigFace size={40} className="drop-shadow" />
          <div>
            <p className="text-lg font-extrabold leading-5">Mommy Bank</p>
            <p className="text-xs font-bold text-ink/40">money &amp; screen time</p>
          </div>
        </button>
        <nav className="flex flex-col gap-1.5 px-3">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} className={linkClass} end={"end" in n ? n.end : false}>
              {n.icon}
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto p-4">
          <div className="card flex items-center gap-3 !p-3">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-piggysoft text-xl">
              {user?.avatar}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-extrabold">{user?.display_name}</p>
              <p className="text-xs font-bold text-ink/40">{isAdmin ? "Parent · admin" : "kid"}</p>
            </div>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="rounded-xl p-2 text-ink/40 hover:bg-piggysoft hover:text-ink"
              aria-label="Log out"
              title="Log out"
            >
              <IconLogout />
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile header */}
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-ink/5 bg-white/80 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2">
          <PigFace size={32} />
          <span className="font-extrabold">Mommy Bank</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xl">{user?.avatar}</span>
          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="rounded-xl p-2 text-ink/40 hover:bg-piggysoft"
            aria-label="Log out"
          >
            <IconLogout />
          </button>
        </div>
      </header>

      <main className="pb-28 lg:pb-10 lg:pl-60">
        <div className="mx-auto w-full max-w-5xl px-4 pt-5 sm:px-6 lg:pt-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom tabs */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex border-t border-ink/5 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden">
        {nav.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={"end" in n ? n.end : false}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2.5 text-[11px] font-bold ${
                isActive ? "text-piggy" : "text-ink/40"
              }`
            }
          >
            {n.icon}
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
