import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../api/auth";
import { Piggy, PigFace } from "../components/art/Piggy";
import { Cloud, FloatingCoins, WaveBackground } from "../components/art/Scene";
import { IconLock, IconSparkle, IconUser } from "../components/art/icons";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [wiggle, setWiggle] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await login(username.trim(), password);
      // navigate by the identity we just logged in as, not the stale closure user
      const role = (data as { user?: { role?: string } }).user?.role;
      navigate(role === "admin" ? "/overview" : "/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setWiggle(true);
      setTimeout(() => setWiggle(false), 600);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4 py-10">
      <WaveBackground />
      <Cloud className="absolute left-[12%] top-[14%] w-32 animate-float" />
      <Cloud className="absolute right-[10%] top-[22%] w-24 animate-float" style={{ animationDelay: "1.4s" }} />
      <FloatingCoins />

      <div className="relative z-10 flex w-full max-w-sm flex-col items-center">
        <Piggy mood="happy" size={150} />
        <h1 className="mt-2 flex items-center gap-2 text-3xl font-extrabold tracking-tight">
          <PigFace size={34} /> Mommy Bank
        </h1>
        <p className="mt-1 text-sm font-bold text-ink/45">
          the family bank for money <IconSparkle size={14} className="inline text-butter" /> and screen time
        </p>

        <form
          onSubmit={onSubmit}
          className={`mt-6 w-full rounded-3xl bg-white p-6 shadow-chunky ring-1 ring-ink/5 ${wiggle ? "animate-wiggle" : ""}`}
        >
          <label className="label" htmlFor="username">
            Username
          </label>
          <div className="relative mb-4">
            <IconUser size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink/30" />
            <input
              id="username"
              className="input pl-11"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="e.g. admin"
              required
            />
          </div>

          <label className="label" htmlFor="password">
            Password
          </label>
          <div className="relative">
            <IconLock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-ink/30" />
            <input
              id="password"
              className="input pl-11 pr-12"
              type={showPw ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              placeholder="••••••••"
              required
            />
            <button
              type="button"
              onClick={() => setShowPw((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-xl px-2 py-1 text-xs font-bold text-piggy-deep hover:bg-piggysoft"
            >
              {showPw ? "hide" : "show"}
            </button>
          </div>

          {error && (
            <p className="mt-3 rounded-2xl bg-red-50 px-4 py-2.5 text-sm font-bold text-red-500" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary mt-5 w-full !py-3.5 text-base">
            {busy ? "Opening the vault…" : "Log in 🐷"}
          </button>
        </form>

        <p className="mt-5 max-w-xs text-center text-xs font-bold text-ink/40">
          Parents manage everything; kids watch their savings grow. Ask Mommy or Daddy if you forgot your password 💕
        </p>
      </div>
    </div>
  );
}
