import { useState } from "react";
import { useAuth } from "../lib/auth-context";
import { DEMO_ACCOUNTS, ROLES } from "../lib/roles";

export default function LoginPage() {
  const { login } = useAuth();
  const [role, setRole] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function pickRole(roleKey) {
    setRole(roleKey); setError("");
    const demo = DEMO_ACCOUNTS.find((a) => a.role === roleKey);
    setUsername(demo?.username ?? ""); setPassword(demo?.password ?? "");
  }
  async function handleSubmit(e) {
    e.preventDefault(); if (!role || !username || !password || busy) return;
    setBusy(true); setError("");
    try { await login(username, password, role); } catch { setError("Credentials or selected role do not match."); } finally { setBusy(false); }
  }
  return (
    <div className="login-page"><div className="login-shell">
      <section className="login-story" aria-label="About Super Agent">
        <div className="login-story__brand app__brand"><span className="app__mark" aria-hidden="true"><b>S</b>A</span><div><h1>Super Agent</h1><p className="app__subtitle">Liquidity intelligence</p></div></div>
        <div className="login-story__copy"><p className="login-story__eyebrow">MFS PROTOTYPE</p><h2>Every signal.<br /><em>One explainable decision.</em></h2><p>Super Agent demonstrates liquidity, operational and risk intelligence using a fully synthetic Bangladesh MFS dataset.</p></div>
        <div className="login-story__statgrid"><div><strong>30 days</strong><span>synthetic observations</span></div><div><strong>3</strong><span>provider balances kept separate</span></div></div>
        <div className="login-story__orb login-story__orb--one" /><div className="login-story__orb login-story__orb--two" />
      </section>
      <section className="login-card">
        <div className="login-card__brand"><p className="login-card__overline">WELCOME BACK</p><h2>Enter your workspace</h2><p className="login-card__intro">Choose a role to load its demo account.</p></div>
        <div className="role-grid">{Object.entries(ROLES).map(([key, r]) => <button key={key} type="button" className={`role-card${role === key ? " role-card--active" : ""}`} onClick={() => pickRole(key)}><r.icon className="role-card__icon" />{r.label}</button>)}</div>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>Username<input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. agent01" autoComplete="username" /></label>
          <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" /></label>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" disabled={busy || !role || !username || !password}>{busy ? "Signing in..." : "Enter workspace"}</button>
        </form>
        <details className="login-demo-hint"><summary>View demo credentials</summary><table><tbody>{DEMO_ACCOUNTS.map((a) => <tr key={a.username}><td>{ROLES[a.role].label}</td><td><code>{a.username}</code></td><td><code>{a.password}</code></td></tr>)}</tbody></table></details>
      </section>
    </div></div>
  );
}
