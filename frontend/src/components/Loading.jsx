export default function Loading({ label = "Loading…" }) {
  return (
    <output className="view-loading">
      <span className="spinner" aria-hidden="true" /> {label}
    </output>
  );
}
