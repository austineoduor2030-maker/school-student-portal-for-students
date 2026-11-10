import { useCallback, useEffect, useState } from "react";

const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000/api").replace(/\/$/, "");
const TOKEN_KEY = "ksu_token";

export const tokenStore = {
  get() {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(t) {
    try { localStorage.setItem(TOKEN_KEY, t); } catch { /* private mode: session just won't persist */ }
  },
  clear() {
    try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ }
  },
};

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data || {};
    this.issues = (data && data.issues) || [];
  }
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = tokenStore.get();
  if (token) headers.Authorization = `Token ${token}`;
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (res.status === 401 && token) {
    tokenStore.clear();
    window.dispatchEvent(new Event("ksu:signed-out"));
  }
  if (!res.ok) {
    const msg = (data && (data.detail || (Array.isArray(data.errors) && data.errors.join(" ")))) || `Request failed (${res.status}).`;
    throw new ApiError(msg, res.status, data);
  }
  return data;
}

/** Load a GET endpoint. `reload()` refetches. */
export function useFetch(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }));
    api(path)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => setState({ data: null, error, loading: false }));
  }, [path]);
  useEffect(load, [load]);
  return { ...state, reload: load };
}
