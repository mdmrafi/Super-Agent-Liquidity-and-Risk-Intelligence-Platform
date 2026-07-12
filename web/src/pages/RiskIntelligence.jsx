import { useCallback, useEffect, useMemo, useState } from 'react';
import { NotebookPen, ShieldAlert } from 'lucide-react';
import { api } from '../api';
import AlertCard from '../components/AlertCard';
import { useAuth } from '../context/AuthContext';
import {
  Empty,
  ErrorState,
  LoadingCards,
  MissingProviderScope,
  nice,
  ProviderAssignment,
  Severity,
} from '../components/ui';

const normalize = (value) => String(value || '').trim().toLowerCase();

export default function RiskIntelligence() {
  const { user } = useAuth();

  if (!user.provider) {
    return (
      <div className='space-y-6'>
        <div>
          <p className='label'>Evidence-first workspace</p>
          <h1 className='mt-2 text-3xl font-semibold'>Risk Intelligence</h1>
        </div>
        <MissingProviderScope role={user.role} />
      </div>
    );
  }

  return (
    <ProviderRiskWorkspace
      key={`${user.username}:${user.provider}`}
      user={user}
      provider={user.provider}
    />
  );
}

function ProviderRiskWorkspace({ user, provider }) {
  const notesKey = `super_agent_risk_notes:${user.username}:${provider}`;
  const [alerts, setAlerts] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState(() => localStorage.getItem(notesKey) || '');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.alerts({
        audience: 'risk_team',
        provider,
      });
      const scoped = response.filter((alert) =>
        normalize(alert.provider) === normalize(provider));
      setAlerts(scoped);
      setSelected(scoped[0] || null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    localStorage.setItem(notesKey, notes);
  }, [notes, notesKey]);

  const events = useMemo(
    () => (selected?.case_history || []).map((event) => ({ ...event, type: 'case' })),
    [selected],
  );

  const update = (updated) => {
    setAlerts((current) => current.map((alert) =>
      alert.alert_id === updated.alert_id ? updated : alert));
    setSelected(updated);
  };

  if (loading) return <LoadingCards />;

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-end justify-between gap-4'>
        <div>
          <p className='label'>Evidence-first workspace</p>
          <h1 className='mt-2 text-3xl font-semibold'>Risk Intelligence</h1>
          <p className='mt-2 text-sm text-slate-500'>
            Unusual activity - requires review. This queue contains {provider}
            evidence only; decisions remain with the analyst.
          </p>
        </div>
        <ProviderAssignment provider={provider} />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      <div className='grid gap-5 xl:grid-cols-[330px_1fr_340px]'>
        <aside className='card h-[calc(100vh-190px)] overflow-y-auto'>
          <div className='sticky top-0 border-b bg-white/90 p-4 backdrop-blur dark:bg-slate-900/90'>
            <p className='font-semibold'>{provider} review queue</p>
            <p className='mt-1 text-xs text-slate-500'>{alerts.length} evidence cards</p>
          </div>
          {alerts.map((alert) => (
            <button
              key={alert.alert_id}
              onClick={() => setSelected(alert)}
              className={`w-full border-b p-4 text-left transition ${selected?.alert_id === alert.alert_id ? 'bg-blue-50 dark:bg-blue-950/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'}`}
            >
              <div className='flex justify-between gap-2'>
                <Severity value={alert.severity} />
                <span className='text-xs font-semibold'>
                  {Math.round(Number(alert.confidence || 0) * 100)}%
                </span>
              </div>
              <p className='mt-3 text-sm font-semibold'>
                Unusual activity - requires review
              </p>
              <p className='mt-1 truncate text-xs text-slate-500'>
                {provider} · {alert.area}
              </p>
            </button>
          ))}
          {!alerts.length && (
            <Empty
              title='No investigations in scope'
              text={`The current API response contains no ${provider} risk cases.`}
            />
          )}
        </aside>

        <main>
          {selected ? (
            <div className='space-y-5'>
              <AlertCard alert={selected} actions onChanged={update} />
              <div className='card p-5'>
                <p className='label'>Confidence meter</p>
                <div className='mt-3 flex items-center gap-4'>
                  <div className='h-3 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800'>
                    <div
                      className='h-full rounded-full bg-blue-600'
                      style={{ width: `${Number(selected.confidence || 0) * 100}%` }}
                    />
                  </div>
                  <b>{Math.round(Number(selected.confidence || 0) * 100)}%</b>
                </div>
                <p className='mt-3 text-xs text-slate-500'>
                  Model confidence is supporting evidence, not a determination.
                </p>
              </div>

              <div className='card p-5'>
                <p className='label mb-5'>Timeline of unusual events</p>
                {events.length ? events.map((event, index) => (
                  <div
                    key={index}
                    className='relative ml-2 border-l-2 pb-6 pl-5 last:pb-0'
                  >
                    <span className='absolute -left-[7px] top-0 h-3 w-3 rounded-full bg-blue-500 ring-4 ring-white dark:ring-slate-900' />
                    <p className='text-sm font-semibold'>{nice(event.action)}</p>
                    <p className='mt-1 text-xs text-slate-500'>
                      {event.actor} · {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                )) : <Empty title='No timeline events' />}
              </div>
            </div>
          ) : (
            <div className='card'>
              <Empty icon={ShieldAlert} title='No investigation selected' />
            </div>
          )}
        </main>

        <aside className='card h-fit p-5'>
          <div className='flex items-center gap-2'>
            <NotebookPen size={18} />
            <h2 className='font-semibold'>Analyst notes</h2>
          </div>
          <p className='mt-2 text-xs leading-5 text-slate-500'>
            Private browser-local notes for {provider}. Notes are isolated by
            account and provider and are not submitted to the API.
          </p>
          <textarea
            className='input mt-4 min-h-64 resize-y'
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder='Record observations, verification steps, and follow-ups…'
          />
          <p className='mt-2 text-right text-xs text-slate-400'>Saved locally</p>
        </aside>
      </div>
    </div>
  );
}
