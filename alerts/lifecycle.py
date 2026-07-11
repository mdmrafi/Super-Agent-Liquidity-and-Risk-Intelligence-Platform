"""Case lifecycle (spec section 8): new -> acknowledged -> escalated -> resolved.

Strict linear order -- each function only allows moving to the immediate next
state (no skipping escalate). Every transition appends one case_history entry.
display_status only reverts to "normal" on reaching resolved; it never
otherwise changes here, and nothing in this module touches whether the agent
can transact.

Functions take an explicit `at` timestamp rather than defaulting to wall-clock
now() -- keeps them pure/deterministic and lets a demo narrate a lifecycle
using the same synthetic timeline as the rest of the data.
"""

_ORDER = ["new", "acknowledged", "escalated", "resolved"]


def _transition(alert, target_status, actor, at):
    current = alert["case_status"]
    if _ORDER.index(target_status) != _ORDER.index(current) + 1:
        raise ValueError(f"cannot transition from '{current}' to '{target_status}'")

    alert = dict(alert)
    alert["case_status"] = target_status
    alert["case_history"] = alert["case_history"] + [
        {"timestamp": str(at), "actor": actor, "action": f"{current} -> {target_status}"}
    ]
    if target_status == "resolved":
        alert["display_status"] = "normal"
    return alert


def acknowledge(alert, actor, at):
    return _transition(alert, "acknowledged", actor, at)


def escalate(alert, actor, at):
    return _transition(alert, "escalated", actor, at)


def resolve(alert, actor, at):
    return _transition(alert, "resolved", actor, at)
