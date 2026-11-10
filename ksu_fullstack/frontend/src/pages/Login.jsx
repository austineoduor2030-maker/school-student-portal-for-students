import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { HOME, useAuth } from "../auth";
import { Banner } from "../components/ui";
import { ThemeButton } from "../components/Layout";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={HOME[user.role]} replace />;

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const u = await login(username.trim(), password);
      nav(HOME[u.role], { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <div className="row"><div className="logo">KSU</div><ThemeButton /></div>
        <h1>Kisii University</h1>
        <p className="sub">AI academic adviser. Sign in with your portal account.</p>
        <Banner>{error}</Banner>
        <label htmlFor="u">Registration number or username</label>
        <input id="u" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus />
        <label htmlFor="p">Password</label>
        <input id="p" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        <button className="btn" style={{ width: "100%", marginTop: 16 }} disabled={busy || !username || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="note">Forgot your password? Contact the ICT office. Accounts are created by staff.</p>
      </form>
    </div>
  );
}
