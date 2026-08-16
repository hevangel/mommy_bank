import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, clearToken, getToken, setToken } from "./client";
import type { AccountView, User } from "./types";

interface AuthState {
  user: User | null;
  account: AccountView | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<{ token: string }>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<AccountView | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(getToken()));

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setAccount(null);
      return;
    }
    try {
      const me = await api.get<{ user: User; account?: AccountView }>("/api/v1/auth/me");
      setUser(me.user);
      setAccount(me.account ?? null);
    } catch {
      clearToken();
      setUser(null);
      setAccount(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string): Promise<{ token: string; user?: { role?: string } }> => {
      const data = await api.post<{ token: string; user?: { role?: string } }>("/api/v1/auth/login", {
        username,
        password,
      });
      setToken(data.token);
      await refresh();
      return data;
    },
    [refresh],
  );

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setAccount(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, account, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
