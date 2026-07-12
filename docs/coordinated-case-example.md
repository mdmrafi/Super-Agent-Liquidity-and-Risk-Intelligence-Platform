# Coordinated Case Example (Scenario D)

*Deliverable for Master Specification §7 (mandatory: "for at least one important
alert, show who receives it, who owns it, the recommended next step, and the final
status"), §11 Scenario D, and §16 submission checklist ("at least one alert
demonstrates routing, ownership, acknowledgement or escalation, and a visible
resolution status").*

This is a **visible artifact**, not a live-only demo: one alert in the shipped
`data/alerts_calibration.json` — **`alert_c00107`** — is deterministically walked
through the full coordination lifecycle by
[alerts/main.py](../backend/alerts/main.py) (`seed_coordinated_example`). Every other alert
stays at `case_status: "new"` (raw detector output). To see it live: open the
**Ops / coordination view**, filter to agent_14 / Shibganj, and open the card.

## The alert

| Field | Value | Answers §7's… |
|---|---|---|
| `alert_id` | `alert_c00107` | — |
| `agent_id` / `area` | agent_14 / Shibganj | — |
| `alert_type` / `liquidity_type` | liquidity_shortage / **physical_cash** | *which* pool: the shared cash drawer |
| `severity` | high | — |
| `evidence` | *"shared physical cash reserve: burn_rate -10,104 BDT/hour, time_to_shortage 0 minutes, confidence 72%"* | the reason, in plain language |
| `audience` | `agent`, `field_officer`, `area_team` | **who can receive and escalate it** |
| `recommended_owner` | `field_officer` | **who receives it** |
| `recommended_action` | `request_replenishment_support` | **the recommended next step** |
| `case_status` | **resolved** | **the final status** |

## The coordination trail (`case_history`)

Append-only, auditable (§8, §5 auditability) — routing → ownership → escalation →
resolution, all within the same afternoon:

| Time | Actor | Transition | Meaning |
|---|---|---|---|
| 11:00 | system | created (new) | detector raises the alert, routed to `field_officer` |
| 11:15 | field_officer_lima | new → acknowledged | field officer **takes ownership** |
| 11:40 | field_officer_lima | acknowledged → escalated | escalates for replenishment support |
| 13:05 | area_coordinator_shibganj | escalated → resolved | area coordinator **closes** the case |

On reaching `resolved`, `display_status` reverts to `normal` — the informational
"constrained — replenishment requested" banner clears automatically. At no point is
the agent blocked or restricted; the whole flow is advisory and human-driven (see
[RESPONSIBLE_DESIGN.md](./RESPONSIBLE_DESIGN.md)).

## Reproducing it

```bash
cd backend
python -m alerts.main    # regenerates all alerts, then seeds this one case
```

The alert selector prefers agent_14's first high-severity shared-cash shortage,
then falls back to the first high shared-cash alert. Coordination timestamps and the resolving coordinator's name are
derived from the alert's own timestamp and area, so the seeded story stays
self-consistent even if the data is regenerated.
