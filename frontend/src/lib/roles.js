import { IconAgent, IconAssistant, IconOps, IconProvider, IconRisk } from "../components/icons";

// One primary dashboard per role, plus the read-only Assistant as a shared
// helper tool for the operational roles. Admin is the only role that sees
// every tab. Mirrors backend/db/models.py's UserRole and the demo accounts
// seeded by backend/db/seed_users.py.
export const ROLES = {
  agent: { label: "Agent", icon: IconAgent, primaryView: "agent", views: ["agent"] },
  field_officer: { label: "Field Officer", icon: IconOps, primaryView: "ops", views: ["ops", "assistant"] },
  provider_ops: { label: "Provider Ops", icon: IconProvider, primaryView: "provider", views: ["provider", "assistant"] },
  risk_team: { label: "Risk Team", icon: IconRisk, primaryView: "risk", views: ["risk", "assistant"] },
  admin: {
    label: "Admin",
    icon: IconAssistant,
    primaryView: "agent",
    views: ["agent", "ops", "provider", "risk", "assistant"],
  },
};

// Demo-only: mirrors backend/db/seed_users.py's MOCK_USERS so the login
// page can show working credentials without a round-trip. Real passwords
// are bcrypt-hashed server-side; this is just the mock demo list.
export const DEMO_ACCOUNTS = [
  { role: "agent", username: "agent01", password: "agent123" },
  { role: "field_officer", username: "fieldofficer", password: "officer123" },
  { role: "provider_ops", username: "providerops", password: "provider123" },
  { role: "risk_team", username: "riskteam", password: "risk123" },
  { role: "admin", username: "admin", password: "admin123" },
];
