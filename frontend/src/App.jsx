import { useEffect, useState } from "react";
import { getMeta } from "./api";
import { LanguageProvider } from "./lib/LanguageContext";
import LanguageToggle from "./components/LanguageToggle";
import AgentView from "./views/AgentView";
import OpsView from "./views/OpsView";
import RiskView from "./views/RiskView";
import AssistantView from "./views/AssistantView";
import "./App.css";

const VIEWS = {
  agent: { label: "Agent view", Component: AgentView },
  ops: { label: "Ops / coordination view", Component: OpsView },
  risk: { label: "Risk / compliance view", Component: RiskView },
  assistant: { label: "Assistant", Component: AssistantView },
};

export default function App() {
  const [split, setSplit] = useState("calibration");
  const [meta, setMeta] = useState(null);
  const [tab, setTab] = useState("agent");

  useEffect(() => {
    getMeta(split).then(setMeta);
  }, [split]);

  const ActiveView = VIEWS[tab].Component;

  return (
    <LanguageProvider>
      <div className="app">
        <header className="app__header">
          <h1>Super Agent Liquidity &amp; Risk Intelligence</h1>
          <div className="app__header-controls">
            <select value={split} onChange={(e) => setSplit(e.target.value)}>
              <option value="calibration">Calibration data</option>
              <option value="holdout">Holdout data</option>
            </select>
            <LanguageToggle />
          </div>
        </header>

        <nav className="app__tabs">
          {Object.entries(VIEWS).map(([key, v]) => (
            <button
              key={key}
              className={key === tab ? "tab active" : "tab"}
              onClick={() => setTab(key)}
              type="button"
            >
              {v.label}
            </button>
          ))}
        </nav>

        <main>
          {meta ? <ActiveView meta={meta} split={split} /> : <p>Loading…</p>}
        </main>
      </div>
    </LanguageProvider>
  );
}
