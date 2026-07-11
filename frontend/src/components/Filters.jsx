export default function Filters({ meta, value, onChange }) {
  function set(key, v) {
    onChange({ ...value, [key]: v || undefined });
  }

  return (
    <div className="filters">
      <label>
        Provider
        <select value={value.provider || ""} onChange={(e) => set("provider", e.target.value)}>
          <option value="">All</option>
          {meta.providers.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </label>

      <label>
        Agent
        <select value={value.agent_id || ""} onChange={(e) => set("agent_id", e.target.value)}>
          <option value="">All</option>
          {meta.agents.map((a) => (
            <option key={a.agent_id} value={a.agent_id}>{a.agent_id}</option>
          ))}
        </select>
      </label>

      <label>
        Area
        <select value={value.area || ""} onChange={(e) => set("area", e.target.value)}>
          <option value="">All</option>
          {meta.areas.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </label>

      <label>
        From
        <input type="date" value={value.start ? value.start.slice(0, 10) : ""}
               onChange={(e) => set("start", e.target.value ? `${e.target.value}T00:00:00` : "")} />
      </label>

      <label>
        To
        <input type="date" value={value.end ? value.end.slice(0, 10) : ""}
               onChange={(e) => set("end", e.target.value ? `${e.target.value}T23:59:59` : "")} />
      </label>

      <button type="button" className="clear-filters" onClick={() => onChange({})}>Clear</button>
    </div>
  );
}
