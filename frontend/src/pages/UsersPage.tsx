import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { UiMode, User } from "../api/types";
import { Badge, Field, Modal, PageLoader, Spinner, Toggle, useToast } from "../components/ui";
import { IconPencil, IconPlus, IconUsers } from "../components/art/icons";

const AVATARS = ["🐷", "🧑‍🚀", "🐰", "🐻", "🦊", "🐼", "🐨", "🦄", "🐙", "🤖", "👾", "🐣", "🦁", "🐳"];

const MODE_HELP: Record<UiMode, string> = {
  teen: "Full detail: charts, tables, loans, exact numbers.",
  kid: "Simple words, big buttons, friendly icons.",
  toddler: "Picture book: giant numbers & stickers only.",
};

function randomPassword(): string {
  const alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const arr = new Uint32Array(14);
  crypto.getRandomValues(arr);
  return Array.from(arr, (n) => alphabet[n % alphabet.length]).join("");
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    api.get<User[]>("/api/v1/users").then(setUsers).catch(() => setUsers([]));
  }, []);
  useEffect(load, [load]);

  if (!users) return <PageLoader />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <IconUsers /> Family
          </h1>
          <p className="text-sm font-bold text-ink/45">add kids, pick their age view, manage passwords</p>
        </div>
        <button className="btn-primary" onClick={() => setCreating(true)}>
          <IconPlus size={18} /> Add family member
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {users.map((u) => (
          <div key={u.id} className="card flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <span className="grid h-14 w-14 place-items-center rounded-3xl bg-piggysoft text-3xl shadow-soft">
                {u.avatar}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-lg font-extrabold">
                  {u.display_name} {!u.is_active && <span className="text-xs text-red-400">(inactive)</span>}
                </p>
                <p className="text-xs font-bold text-ink/40">@{u.username}</p>
              </div>
              <button
                className="rounded-2xl p-2 text-ink/40 hover:bg-piggysoft hover:text-ink"
                onClick={() => setEditing(u)}
                aria-label={`edit ${u.display_name}`}
              >
                <IconPencil size={18} />
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <Badge tone={u.role === "admin" ? "piggy" : "sky"}>{u.role}</Badge>
              <Badge tone={u.ui_mode === "teen" ? "lav" : u.ui_mode === "kid" ? "mint" : "butter"}>
                {u.ui_mode}
              </Badge>
              {u.can_convert && <Badge tone="mint">convert ✓</Badge>}
              {u.can_borrow && <Badge tone="lav">borrow ✓</Badge>}
            </div>
          </div>
        ))}
      </div>

      {creating && <UserForm onClose={() => setCreating(false)} onSaved={load} />}
      {editing && <UserForm user={editing} onClose={() => setEditing(null)} onSaved={load} />}
    </div>
  );
}

function UserForm({
  user,
  onClose,
  onSaved,
}: {
  user?: User;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [username, setUsername] = useState(user?.username ?? "");
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(user?.role ?? "user");
  const [uiMode, setUiMode] = useState<UiMode>(user?.ui_mode ?? "teen");
  const [avatar, setAvatar] = useState(user?.avatar ?? "🐷");
  const [canConvert, setCanConvert] = useState(user?.can_convert ?? true);
  const [canBorrow, setCanBorrow] = useState(user?.can_borrow ?? false);
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    try {
      if (user) {
        await api.patch(`/api/v1/users/${user.id}`, {
          display_name: displayName,
          role,
          ui_mode: uiMode,
          avatar,
          can_convert: canConvert,
          can_borrow: canBorrow,
          is_active: isActive,
          ...(password ? { password } : {}),
        });
        toast(`${displayName} updated ✅`);
      } else {
        if (!/^[A-Za-z0-9_.-]{2,32}$/.test(username)) throw new Error("Username: 2-32 letters/numbers");
        if (password.length < 4) throw new Error("Password needs 4+ characters");
        await api.post("/api/v1/users", {
          username,
          password,
          display_name: displayName || username,
          role,
          ui_mode: uiMode,
          avatar,
          can_convert: canConvert,
          can_borrow: canBorrow,
        });
        toast(`${displayName || username} joined the family bank! 🎉`);
      }
      onSaved();
      onClose();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed", "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={user ? `Edit ${user.display_name}` : "Add a family member"}>
      <div className="flex flex-col gap-4">
        {!user && (
          <Field label="Username (for login)">
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. bigbro" />
          </Field>
        )}
        <Field label="Display name">
          <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="e.g. Big Bro" />
        </Field>
        <Field label={user ? "Reset password (leave blank to keep)" : "Password"} hint={user ? undefined : "4+ characters — something the kid can type"}>
          <div className="flex gap-2">
            <input
              className="input"
              type="text"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={user ? "unchanged" : "type or generate"}
            />
            <button type="button" className="btn-ghost shrink-0 !py-2 text-xs" onClick={() => setPassword(randomPassword())}>
              ✨ generate
            </button>
          </div>
        </Field>
        <Field label="Role">
          <div className="flex rounded-2xl bg-cream p-1">
            {(["user", "admin"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`flex-1 rounded-xl px-3 py-2 text-sm font-bold ${role === r ? "bg-white shadow-soft" : "text-ink/45"}`}
              >
                {r === "user" ? "🧒 kid (read-only)" : "👑 parent (admin)"}
              </button>
            ))}
          </div>
        </Field>
        <Field label="Age view" hint={MODE_HELP[uiMode]}>
          <div className="flex rounded-2xl bg-cream p-1">
            {(["teen", "kid", "toddler"] as UiMode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => {
                  setUiMode(m);
                  if (m === "toddler") setCanConvert(false);
                }}
                className={`flex-1 rounded-xl px-2 py-2 text-sm font-bold capitalize ${uiMode === m ? "bg-white shadow-soft" : "text-ink/45"}`}
              >
                {m === "teen" ? "🧑 teen" : m === "kid" ? "🧒 kid" : "🧸 toddler"}
              </button>
            ))}
          </div>
        </Field>
        <Field label="Avatar">
          <div className="flex flex-wrap gap-1.5">
            {AVATARS.map((a) => (
              <button
                key={a}
                type="button"
                onClick={() => setAvatar(a)}
                className={`grid h-10 w-10 place-items-center rounded-2xl text-xl transition-all ${
                  avatar === a ? "bg-piggysoft ring-2 ring-piggy" : "bg-cream hover:bg-piggysoft/50"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
        </Field>
        <div className="flex flex-col gap-2.5 rounded-2xl bg-cream p-4">
          <Toggle checked={canConvert} onChange={setCanConvert} label="Kid can convert money → screen time" />
          <Toggle checked={canBorrow} onChange={setCanBorrow} label="Kid can borrow (needs borrowing enabled too)" />
          {user && <Toggle checked={isActive} onChange={setIsActive} label="Account active" />}
        </div>
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" disabled={busy || !displayName} onClick={save}>
            {busy && <Spinner className="h-4 w-4" />} {user ? "Save changes" : "Add member"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
