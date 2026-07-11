export function formatBDT(amount) {
  return new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 }).format(amount) + " BDT";
}

export function formatDateTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export function describeCohortContext(context, peerCount) {
  switch (context) {
    case "agent_only":
      return `Isolated to this agent — compared against ${peerCount} similar agents, none show the same pattern`;
    case "area_wide":
      return `Shared pattern — ${peerCount}+ nearby agents in this area show similar pressure`;
    case "provider_wide":
      return `Shared across this provider — agents in other areas show the same pattern too`;
    case "self_history_fallback":
      return peerCount > 0
        ? `Too few comparable agents nearby (just ${peerCount}) — compared against this agent's own history instead`
        : `No comparable agents nearby — compared against this agent's own history instead`;
    default:
      return context;
  }
}

// Fixed categorical order (never cycled/reassigned), identity chips: solid
// fill + inverse ink. Referenced as CSS custom properties so the light/dark
// step swaps in one place (index.css) instead of a second hex table here.
export const PROVIDER_COLORS = {
  bKash: "var(--cat-blue)",
  Nagad: "var(--cat-violet)",
  Rocket: "var(--cat-aqua)",
};
export const PROVIDER_TEXT = "var(--ink-inverse)";
export const CASH_COLOR = "var(--cat-cash)";

// Status palette (reserved -- never reused as a categorical hue). Rendered
// as soft pills (tinted wash + saturated ink) rather than solid fill: the
// wash/ink pair is contrast-safe in both themes by construction, where a
// solid fill would need a different text color per status per theme.
export const SEVERITY_BG = {
  high: "var(--status-critical-wash)",
  medium: "var(--status-warning-wash)",
  low: "var(--status-good-wash)",
};
export const SEVERITY_TEXT = {
  high: "var(--status-critical-ink)",
  medium: "var(--status-warning-ink)",
  low: "var(--status-good-ink)",
};
