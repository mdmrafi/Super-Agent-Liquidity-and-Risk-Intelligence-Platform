import { useCallback, useEffect, useState } from "react";
import { getMeta } from "./api";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import { LanguageProvider } from "./lib/LanguageContext";
import { ROLES } from "./lib/roles";
import { IconAgent, IconOps, IconProvider, IconRisk, IconAssistant } from "./components/icons";
import LanguageToggle from "./components/LanguageToggle";
import Loading from "./components/Loading";
import LoginPage from "./views/LoginPage";
import AgentView from "./views/AgentView";
import OpsView from "./views/OpsView";
import ProviderOpsView from "./views/ProviderOpsView";
import RiskView from "./views/RiskView";
import AssistantView from "./views/AssistantView";
import "./App.css";

const VIEWS = {
  agent: { label: "Agent view", Icon: IconAgent, Component: AgentView },
  ops: { label: "Ops / coordination", Icon: IconOps, Component: OpsView },
  provider: { label: "Provider ops", Icon: IconProvider, Component: ProviderOpsView },
  risk: { label: "Risk / compliance", Icon: IconRisk, Component: RiskView },
  assistant: { label: "Assistant", Icon: IconAssistant, Component: AssistantView },
};

function Dashboard() {
  const { user, logout } = useAuth();
  const roleConfig = ROLES[user.role];
  const allowedTabs = roleConfig.views;

  const [split, setSplit] = useState("calibration");
  const [meta, setMeta] = useState(null);
  const [metaError, setMetaError] = useState(null);
  const [tab, setTab] = useState(roleConfig.primaryView);
  const [loadToken, setLoadToken] = useState(0);

  const reload = useCallback(() => setLoadToken((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setMetaError(null);
    getMeta(split)
      .then((m) => {
        if (!cancelled) setMeta(m);
      })
      .catch((e) => {
        if (!cancelled) setMetaError(e.message || String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [split, loadToken]);

  const ActiveView = VIEWS[tab].Component;

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__brand">
          <span className="app__mark" aria-hidden="true">SA</span>
          <div>
            <h1>Super Agent</h1>
            <p className="app__subtitle">Liquidity &amp; risk intelligence · Sylhet MFS agent network</p>
          </div>
        </div>
        <div className="app__header-controls">
          <label className="split-select">
            <span className="visually-hidden">Data split</span>
            <select value={split} onChange={(e) => setSplit(e.target.value)}>
              <option value="calibration">Calibration data</option>
              <option value="holdout">Holdout data</option>
            </select>
          </label>
          <LanguageToggle />
          <div className="user-badge">
            <span className="user-badge__name">{user.display_name}</span>
            <span className="user-badge__role">{roleConfig.label}</span>
          </div>
          <button type="button" className="logout-btn" onClick={logout}>Log out</button>
        </div>
      </header>

      <nav className="app__tabs" aria-label="Views">
        {allowedTabs.map((key) => {
          const v = VIEWS[key];
          return (
            <button
              key={key}
              className={key === tab ? "tab active" : "tab"}
              onClick={() => setTab(key)}
              type="button"
              aria-current={key === tab ? "page" : undefined}
            >
              <v.Icon className="tab__icon" />
              {v.label}
            </button>
          );
        })}
      </nav>

      <main>
        {metaError && (
          <div className="conn-error" role="alert">
            <div>
              <strong>Can't reach the backend.</strong>
              <p>{metaError}</p>
              <p className="muted">
                Is the API running? From <code>backend/</code>: <code>python -m api.main</code>
                {" "}(port {import.meta.env.VITE_BACKEND_PORT || "8000"}, set via <code>BACKEND_PORT</code> in .env)
              </p>
            </div>
            <button type="button" onClick={reload}>Retry</button>
          </div>
        )}
        {!meta && !metaError && <Loading />}
        {meta && <ActiveView meta={meta} split={split} user={user} />}
      </main>
    </div>
  );
}

function AuthGate() {
  const { user, restoring } = useAuth();
  if (restoring) return <Loading label="Signing you in…" />;
  if (!user) return <LoginPage />;
  return <Dashboard />;
}

export default function App() {
  return (
    <AuthProvider>
      <LanguageProvider>
        <AuthGate />
      </LanguageProvider>
    </AuthProvider>
  );
}
