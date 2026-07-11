import { useState } from "react";
import { useAuth } from "../lib/AuthContext";
import { DEMO_ACCOUNTS, ROLES } from "../lib/roles";

export default function LoginPage() {
  const { login } = useAuth();
  const [role, setRole] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function pickRole(roleKey) {
    setRole(roleKey);
    setError("");
    const demo = DEMO_ACCOUNTS.find((a) => a.role === roleKey);
    setUsername(demo?.username ?? "");
    setPassword(demo?.password ?? "");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username || !password || busy) return;
    setBusy(true);
    setError("");
    try {
      await login(username, password);
    } catch {
      setError("Incorrect username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="app__brand login-card__brand">
          <span className="app__mark" aria-hidden="true">SA</span>
          <div>
            <h1>Super Agent</h1>
            <p className="app__subtitle">Liquidity &amp; risk intelligence</p>
          </div>
        </div>

        <p className="login-card__intro">Select your role to sign in.</p>

        <div className="role-grid">
          {Object.entries(ROLES).map(([key, r]) => (
            <button
              key={key}
              type="button"
              className={`role-card${role === key ? " role-card--active" : ""}`}
              onClick={() => pickRole(key)}
            >
              <r.icon className="role-card__icon" />
              {r.label}
            </button>
          ))}
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. agent01"
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" disabled={busy || !username || !password}>
            {busy ? "Signing in…" : "Log in"}
          </button>
        </form>

        <details className="login-demo-hint">
          <summary>Demo credentials</summary>
          <table>
            <tbody>
              {DEMO_ACCOUNTS.map((a) => (
                <tr key={a.username}>
                  <td>{ROLES[a.role].label}</td>
                  <td><code>{a.username}</code></td>
                  <td><code>{a.password}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      </div>
    </div>
  );
}
