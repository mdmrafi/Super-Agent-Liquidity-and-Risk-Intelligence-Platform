import { useState } from 'react';
import {
  FileText, LoaderCircle, UserPlus, History, StickyNote,
} from 'lucide-react';
import { api } from '../api';
import { dateTime, nice, Severity, Status } from './ui';

// Ownership history = the subset of case_history entries that record an
// assignment (they carry new_owner + reason), rendered with the required
// audit fields: previous owner, new owner, actor, timestamp, reason.
function ownershipHistory(alert) {
  return (alert.case_history || []).filter((h) => h.new_owner);
}

export default function AlertCard({ alert, onChanged, actions = false, resolve = false }) {
  const [explanation, setExplanation] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  // assignment state
  const [assignOpen, setAssignOpen] = useState(false);
  const [assignees, setAssignees] = useState(null);
  const [pickOwner, setPickOwner] = useState('');
  const [reason, setReason] = useState('');

  // note state
  const [noteText, setNoteText] = useState('');

  async function explain() {
    setBusy('explain');
    setError('');
    try {
      setExplanation((await api.explain(alert.alert_id)).explanation);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  async function runAction(name) {
    setBusy(name);
    setError('');
    try {
      onChanged?.(await api.action(alert.alert_id, name));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  async function openAssign() {
    setAssignOpen((open) => !open);
    if (assignees === null) {
      try {
        const list = await api.assignees(alert.alert_id);
        setAssignees(list);
        setPickOwner(list[0]?.username || '');
      } catch (e) {
        setError(e.message);
        setAssignees([]);
      }
    }
  }

  async function submitAssign(event) {
    event.preventDefault();
    if (!pickOwner || !reason.trim()) return;
    setBusy('assign');
    setError('');
    try {
      onChanged?.(await api.assign(alert.alert_id, pickOwner, reason.trim()));
      setReason('');
      setAssignOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  async function submitNote(event) {
    event.preventDefault();
    if (!noteText.trim()) return;
    setBusy('note');
    setError('');
    try {
      onChanged?.(await api.note(alert.alert_id, noteText.trim()));
      setNoteText('');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }

  const owners = ownershipHistory(alert);
  const notes = alert.case_notes || [];

  return (
    <article className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Severity value={alert.severity} />
            <Status value={alert.case_status} />
            <span className="text-xs text-slate-400">{alert.alert_id}</span>
          </div>
          <h3 className="mt-3 font-semibold">
            {nice(alert.alert_type)} · {alert.provider || 'Physical Cash'}
          </h3>
          <p className="mt-1 text-sm text-slate-500">
            {alert.agent_id} · {alert.area} · {dateTime(alert.timestamp)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold">{Math.round((alert.confidence || 0) * 100)}%</p>
          <p className="label">confidence</p>
        </div>
      </div>

      <div className="mt-4 rounded-xl bg-slate-50 p-3 dark:bg-slate-950/60">
        <p className="label mb-2">Evidence</p>
        {(alert.evidence || []).map((x, i) => (
          <p key={i} className="text-sm leading-6 text-slate-600 dark:text-slate-300">{x}</p>
        ))}
      </div>

      {/* Owner: stable identifier of record, plus the role routing recommends */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span>
          <span className="label mr-1 inline">Owner</span>
          <b>{alert.case_owner_display || 'Unassigned'}</b>
        </span>
        <span className="text-slate-500">
          Recommended: {nice(alert.recommended_owner || '—')}
        </span>
      </div>

      {explanation && (
        <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm leading-6 text-blue-900 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-200">
          {explanation}
        </div>
      )}
      {error && <p className="mt-3 text-xs text-rose-600">{error}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        <button disabled={!!busy} onClick={explain} className="btn-secondary">
          <FileText size={16} />
          {busy === 'explain' ? 'Explaining…' : 'Explain in plain language'}
        </button>
        {actions && (
          <>
            <button
              disabled={!!busy || alert.case_status !== 'new'}
              onClick={() => runAction('acknowledge')}
              className="btn-secondary"
            >
              {busy === 'acknowledge' ? <LoaderCircle className="animate-spin" size={16} /> : null}
              Acknowledge
            </button>
            <button
              disabled={!!busy || !['new', 'acknowledged'].includes(alert.case_status)}
              onClick={() => runAction('escalate')}
              className="btn-secondary"
            >
              Escalate
            </button>
            {resolve && (
              <button
                disabled={!!busy || !['acknowledged', 'escalated'].includes(alert.case_status)}
                onClick={() => runAction('resolve')}
                className="btn-primary"
              >
                Resolve
              </button>
            )}
            <button disabled={!!busy} onClick={openAssign} className="btn-secondary">
              <UserPlus size={16} />
              {alert.case_owner ? 'Reassign owner' : 'Assign owner'}
            </button>
          </>
        )}
      </div>

      {actions && assignOpen && (
        <form onSubmit={submitAssign} className="mt-3 rounded-xl border p-3 dark:border-slate-700">
          <label className="label block" htmlFor={`assignee-${alert.alert_id}`}>Assign to</label>
          <select
            id={`assignee-${alert.alert_id}`}
            className="input mt-2"
            value={pickOwner}
            onChange={(e) => setPickOwner(e.target.value)}
            disabled={assignees === null}
          >
            {assignees === null && <option>Loading…</option>}
            {assignees?.map((c) => (
              <option key={c.username} value={c.username}>
                {c.display_name} — {nice(c.role)}
              </option>
            ))}
          </select>
          <input
            className="input mt-2"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason for (re)assignment — required, recorded in the audit trail"
          />
          <div className="mt-2 flex gap-2">
            <button type="submit" disabled={!!busy || !pickOwner || !reason.trim()} className="btn-primary">
              {busy === 'assign' ? <LoaderCircle className="animate-spin" size={16} /> : null}
              Save assignment
            </button>
            <button type="button" onClick={() => setAssignOpen(false)} className="btn-secondary">Cancel</button>
          </div>
        </form>
      )}

      {owners.length > 0 && (
        <div className="mt-4">
          <p className="label mb-2 flex items-center gap-1.5"><History size={13} /> Ownership history</p>
          <div className="space-y-2">
            {owners.map((h, i) => (
              <div key={i} className="border-l-2 border-slate-200 pl-3 text-sm dark:border-slate-700">
                <b>{h.previous_owner || 'unassigned'} → {h.new_owner}</b>
                <p className="mt-0.5 text-xs text-slate-500">
                  {h.actor} · {dateTime(h.timestamp)}
                </p>
                {h.reason && <p className="mt-0.5 text-xs italic text-slate-500">“{h.reason}”</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4">
        <p className="label mb-2 flex items-center gap-1.5"><StickyNote size={13} /> Case notes</p>
        {notes.length > 0 ? (
          <div className="space-y-2">
            {notes.map((n, i) => (
              <div key={i} className="border-l-2 border-slate-200 pl-3 text-sm dark:border-slate-700">
                <p className="text-slate-600 dark:text-slate-300">{n.text}</p>
                <p className="mt-0.5 text-xs text-slate-500">{n.actor} · {dateTime(n.timestamp)}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No notes yet.</p>
        )}
        {actions && (
          <form onSubmit={submitNote} className="mt-2 flex gap-2">
            <input
              className="input"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a coordination note…"
            />
            <button type="submit" disabled={!!busy || !noteText.trim()} className="btn-secondary">
              {busy === 'note' ? <LoaderCircle className="animate-spin" size={16} /> : 'Add note'}
            </button>
          </form>
        )}
      </div>
    </article>
  );
}
