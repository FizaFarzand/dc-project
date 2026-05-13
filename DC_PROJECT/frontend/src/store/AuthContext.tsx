import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getErrorMessage } from "../services/api";
import type { UserMe } from "../types";

type AuthContextValue = {
  user: UserMe | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem("access_token"),
  );
  const [user, setUser] = useState<UserMe | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ---------------- GET CURRENT USER ----------------
  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setUser(null);
      return;
    }

    const { data } = await api.get<UserMe>("/me");
    setUser(data);
  }, []);

  // ---------------- LOGIN ----------------
  const doLogin = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<{ access_token: string }>("/login", {
      email,
      password,
    });

    localStorage.setItem("access_token", data.access_token);
    setToken(data.access_token);

    const { data: me } = await api.get<UserMe>("/me");
    setUser(me);
  }, []);

  // ---------------- REGISTER ----------------
  const doRegister = useCallback(
    async (name: string, email: string, password: string) => {
      await api.post("/register", {
        name,
        email,
        password,
        role: "customer",
      });

      await doLogin(email, password);
    },
    [doLogin],
  );

  // ---------------- AUTO LOAD USER ----------------
  useEffect(() => {
    let cancelled = false;

    (async () => {
      const t = localStorage.getItem("access_token");

      if (!t) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const { data } = await api.get<UserMe>("/me");
        if (!cancelled) setUser(data);
      } catch {
        if (!cancelled) {
          setUser(null);
          localStorage.removeItem("access_token");
          setToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // ---------------- WRAPPERS ----------------
  const login = useCallback(
    async (email: string, password: string) => {
      try {
        setError(null);
        await doLogin(email, password);
      } catch (e) {
        setError(getErrorMessage(e));
        throw e;
      }
    },
    [doLogin],
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      try {
        setError(null);
        await doRegister(name, email, password);
      } catch (e) {
        setError(getErrorMessage(e));
        throw e;
      }
    },
    [doRegister],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  const refreshUserWrapped = useCallback(async () => {
    try {
      await refreshUser();
    } catch {
      setUser(null);
    }
  }, [refreshUser]);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      error,
      login,
      register,
      logout,
      refreshUser: refreshUserWrapped,
      clearError,
    }),
    [
      user,
      token,
      loading,
      error,
      login,
      register,
      logout,
      refreshUserWrapped,
      clearError,
    ],
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}