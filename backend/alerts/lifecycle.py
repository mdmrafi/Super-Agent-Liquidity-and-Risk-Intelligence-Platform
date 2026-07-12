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


def add_note(alert, actor, text, at):
    """Append a free-text case note. Distinct from case_history: notes are
    analyst commentary, not a case_status transition, so case_status and
    display_status are untouched."""
    alert = dict(alert)
    alert["case_notes"] = alert.get("case_notes", []) + [
        {"timestamp": str(at), "actor": actor, "text": text}
    ]
    return alert


def assign(alert, actor, new_owner, new_owner_display, reason, at):
    """Assign or reassign the accountable owner of a case.

    Records an append-only audit event in case_history capturing the previous
    owner, the new owner, the actor who made the change, the timestamp, and the
    required reason. case_status/display_status are untouched -- ownership is an
    orthogonal axis to the new->acknowledged->escalated->resolved lifecycle.
    History is never edited or deleted in place; every change is a new entry."""
    previous_owner = alert.get("case_owner")
    alert = dict(alert)
    alert["case_owner"] = new_owner
    alert["case_owner_display"] = new_owner_display
    verb = "assigned" if previous_owner is None else "reassigned"
    alert["case_history"] = alert["case_history"] + [
        {
            "timestamp": str(at),
            "actor": actor,
            "action": f"owner {verb}: {previous_owner or 'unassigned'} -> {new_owner}",
            "previous_owner": previous_owner,
            "new_owner": new_owner,
            "reason": reason,
        }
    ]
    return alert
