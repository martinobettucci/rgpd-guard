// @spec docs/BACKLOG.md#RG-012 | docs/BACKLOG.md#RG-013 | docs/DAT.md#securite
// État de session du tableau de bord : lu auprès du moteur, jamais stocké dans le navigateur.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./lib/api";

interface AuthState {
  status: "checking" | "anonymous" | "authenticated";
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  expire: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState["status"]>("checking");

  useEffect(() => {
    api
      .session()
      .then((data) => setStatus(data.authenticated ? "authenticated" : "anonymous"))
      .catch(() => setStatus("anonymous"));
  }, []);

  const login = useCallback(async (token: string) => {
    await api.login(token);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    await api.logout().catch(() => undefined);
    setStatus("anonymous");
  }, []);

  const expire = useCallback(() => setStatus("anonymous"), []);

  return <AuthContext.Provider value={{ status, login, logout, expire }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider manquant");
  return value;
}
