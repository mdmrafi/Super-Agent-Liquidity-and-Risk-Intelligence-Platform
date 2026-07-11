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

export const PROVIDER_COLORS = {
  bKash: "#d6336c",
  Nagad: "#e8590c",
  Rocket: "#7048e8",
};

export const SEVERITY_COLORS = {
  high: "#c92a2a",
  medium: "#e8590c",
  low: "#2f9e44",
};
