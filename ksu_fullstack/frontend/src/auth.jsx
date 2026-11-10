import { createContext, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "./api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export const HOME = { student: "/student", lecturer: "/lecturer", hod: "/hod", staff: "/staff" };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  useEffect(() => {
    if (!tokenStore.get()) return;
    api("/me/")
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const out = () => setUser(null);
    window.addEventListener("ksu:signed-out", out);
    return () => window.removeEventListener("ksu:signed-out", out);
  }, []);

  async function login(username, password) {
    const data = await api("/auth/login/", { method: "POST", body: { username, password } });
    tokenStore.set(data.token);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    try { await api("/auth/logout/", { method: "POST" }); } catch { /* token may already be gone */ }
    tokenStore.clear();
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
