import { useCallback, useEffect, useState } from "react";
import { getMeta } from "./api";
import { AuthProvider } from "./lib/AuthContext";
import { useAuth } from "./lib/auth-context";
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

const VIEW_COPY = {
  agent: { eyebrow: "Agent cockpit", title: "Your liquidity, in one clear view", text: "See your available cash, provider float and support cases without interrupting normal operations." },
  ops: { eyebrow: "Network command", title: "Coordinate the network with confidence", text: "Review computed signals, prioritise cases and keep field operations moving." },
  provider: { eyebrow: "Provider command", title: "Protect provider float", text: "Monitor provider-facing liquidity pressure and route the right response fast." },
  risk: { eyebrow: "Risk intelligence", title: "Review signals, not assumptions", text: "Investigate unusual activity with clear evidence and an auditable case trail." },
  assistant: { eyebrow: "Intelligence assistant", title: "Ask the network anything", text: "Get a plain-language read on the signals already detected by Super Agent." },
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
    getMeta(split).then((m) => { if (!cancelled) setMeta(m); }).catch((e) => { if (!cancelled) setMetaError(e.message || String(e)); });
    return () => { cancelled = true; };
  }, [split, loadToken]);

  const ActiveView = VIEWS[tab].Component;
  const viewCopy = VIEW_COPY[tab];

  return (
    <div className="app">
      <aside className="app__sidebar">
        <div className="app__brand">
          <span className="app__mark" aria-hidden="true"><b>S</b>A</span>
          <div><h1>Super Agent</h1><p className="app__subtitle">Intelligence platform</p></div>
        </div>
        <div className="sidebar__network-status"><span /> Synthetic prototype dataset</div>
        <nav className="app__tabs" aria-label="Views">
          <p className="sidebar__label">Workspace</p>
          {allowedTabs.map((key) => {
            const v = VIEWS[key];
            return <button key={key} className={key === tab ? "tab active" : "tab"} onClick={() => setTab(key)} type="button" aria-current={key === tab ? "page" : undefined}><v.Icon className="tab__icon" /><span>{v.label}</span></button>;
          })}
        </nav>
        <div className="sidebar__footer"><div className="sidebar__footer-dot" /><div><strong>Secure workspace</strong><span>Role-based access</span></div></div>
      </aside>

      <section className="app__content">
        <header className="app__header">
          <div className="mobile-brand app__brand"><span className="app__mark" aria-hidden="true"><b>S</b>A</span><div><h1>Super Agent</h1><p className="app__subtitle">Intelligence platform</p></div></div>
          <div className="app__header-title"><p>Super Agent / <span>{viewCopy.eyebrow}</span></p></div>
          <div className="app__header-controls">
            <label className="split-select"><span className="visually-hidden">Data split</span><select value={split} onChange={(e) => setSplit(e.target.value)}><option value="calibration">Calibration data</option><option value="holdout">Holdout data</option></select></label>
            <LanguageToggle />
            <div className="user-badge"><span className="user-badge__name">{user.display_name}</span><span className="user-badge__role">{roleConfig.label}</span></div>
            <button type="button" className="logout-btn" onClick={logout}>Log out</button>
          </div>
        </header>

        <main>
          <div className="page-intro">
            <div><p className="page-intro__eyebrow">{viewCopy.eyebrow}</p><h2>{viewCopy.title}</h2><p>{viewCopy.text}</p></div>
            <div className="page-intro__signal"><span className="page-intro__pulse" /><div><strong>Prototype snapshot</strong><small>{split} synthetic dataset</small></div></div>
          </div>
          {metaError && <div className="conn-error" role="alert"><div><strong>Can't reach the backend.</strong><p>{metaError}</p><p className="muted">Is the API running? From <code>backend/</code>: <code>python -m api.main</code> (port {import.meta.env.VITE_BACKEND_PORT || "8000"}).</p></div><button type="button" onClick={reload}>Retry</button></div>}
          {!meta && !metaError && <Loading />}
          {meta && <ActiveView meta={meta} split={split} user={user} />}
        </main>
      </section>
    </div>
  );
}

function AuthGate() {
  const { user, restoring } = useAuth();
  if (restoring) return <Loading label="Signing you in..." />;
  if (!user) return <LoginPage />;
  return <Dashboard />;
}

export default function App() {
  return <AuthProvider><LanguageProvider><AuthGate /></LanguageProvider></AuthProvider>;
}
