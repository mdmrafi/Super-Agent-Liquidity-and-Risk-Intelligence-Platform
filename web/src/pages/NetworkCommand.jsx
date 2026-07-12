import { useCallback, useEffect, useMemo, useState } from 'react';
import { Filter, MapPin, RotateCcw } from 'lucide-react';
import { api } from '../api';
import { SeverityChart } from '../components/Charts';
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
  Status,
} from '../components/ui';

const normalize = (value) => String(value ?? '').trim().toLowerCase();
const severityOptions = ['critical', 'high', 'medium', 'low'];

export default function NetworkCommand() {
  const { user } = useAuth();
  const provider = user.provider;
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({ area: '', severity: '', owner: '' });
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    setSelected(null);
    if (!provider) {
      setAlerts([]);
      setLoading(false);
      return;
    }
    try {
      const response = await api.alerts({
        audience: 'field_officer',
        provider,
      });
      setAlerts(response.filter((alert) =>
        normalize(alert.provider) === normalize(provider)));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    load();
  }, [load]);

  // Area options come from the inbox itself, so every option has results.
  const areaOptions = useMemo(
    () => [...new Set(alerts.map((alert) => alert.area).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b)),
    [alerts],
  );

  // Owner options come from the inbox itself; the special __unassigned__ value
  // filters cases that no one has taken ownership of yet.
  const ownerOptions = useMemo(
    () => [...new Map(alerts
      .filter((alert) => alert.case_owner)
      .map((alert) => [alert.case_owner, alert.case_owner_display || alert.case_owner]))
      .entries()].sort((a, b) => a[1].localeCompare(b[1])),
    [alerts],
  );

  const shown = useMemo(
    () => alerts.filter((alert) => {
      const areaMatches = !filters.area
        || normalize(alert.area) === normalize(filters.area);
      const severityMatches = !filters.severity
        || normalize(alert.severity) === normalize(filters.severity);
      const ownerMatches = !filters.owner
        || (filters.owner === '__unassigned__'
          ? !alert.case_owner
          : alert.case_owner === filters.owner);
      return areaMatches && severityMatches && ownerMatches;
    }),
    [alerts, filters],
  );

  const areaHeat = useMemo(
    () => areaOptions.map((area) => ({
      area,
      count: alerts.filter((alert) =>
        normalize(alert.area) === normalize(area)
        && alert.case_status !== 'resolved').length,
    })).sort((a, b) => b.count - a.count),
    [alerts, areaOptions],
  );

  const updateFilter = (key, value) =>
    setFilters((current) => ({ ...current, [key]: value }));
  const updateAlert = (updated) => {
    setAlerts((current) => current.map((alert) =>
      alert.alert_id === updated.alert_id ? updated : alert));
    setSelected(updated);
  };

  if (!provider) {
    return (
      <div className='space-y-6'>
        <div>
          <p className='label'>Field operations</p>
          <h1 className='mt-2 text-3xl font-semibold'>Network Command</h1>
        </div>
        <MissingProviderScope role={user.role} />
      </div>
    );
  }

  if (loading) return <LoadingCards />;

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-end justify-between gap-4'>
        <div>
          <p className='label'>Field operations</p>
          <h1 className='mt-2 text-3xl font-semibold'>Network Command</h1>
          <p className='mt-2 text-sm text-slate-500'>
            Triage {provider} cases across operational areas. Other provider
            records are outside this account's access scope.
          </p>
        </div>
        <ProviderAssignment provider={provider} />
      </div>
      {error && <ErrorState message={error} onRetry={load} />}
      <div className='grid gap-5 xl:grid-cols-[250px_1fr_360px]'>
        <aside className='card h-fit p-4'>
          <div className='flex items-center justify-between gap-2'>
            <div className='flex items-center gap-2 font-semibold'>
              <Filter size={17} /> Filters
            </div>
          </div>

          {(filters.area || filters.severity || filters.owner) && (
            <button
              type='button'
              onClick={() => setFilters({ area: '', severity: '', owner: '' })}
              className='mt-3 inline-flex items-center gap-1 text-xs font-medium text-blue-600'
            >
              <RotateCcw size={13} /> Clear filters
            </button>
          )}

          <label className='label mt-5 block' htmlFor='area-filter'>Area</label>
          <select
            id='area-filter'
            className='input mt-2'
            value={filters.area}
            onChange={(event) => updateFilter('area', event.target.value)}
          >
            <option value=''>All areas</option>
            {areaOptions.map((area) => (
              <option value={area} key={area}>{area}</option>
            ))}
          </select>

          <label className='label mt-4 block' htmlFor='severity-filter'>
            Risk level
          </label>
          <select
            id='severity-filter'
            className='input mt-2'
            value={filters.severity}
            onChange={(event) => updateFilter('severity', event.target.value)}
          >
            <option value=''>All risk levels</option>
            {severityOptions.map((severity) => (
              <option value={severity} key={severity}>{nice(severity)}</option>
            ))}
          </select>

          <label className='label mt-4 block' htmlFor='owner-filter'>Owner</label>
          <select
            id='owner-filter'
            className='input mt-2'
            value={filters.owner}
            onChange={(event) => updateFilter('owner', event.target.value)}
          >
            <option value=''>All owners</option>
            <option value='__unassigned__'>Unassigned</option>
            {ownerOptions.map(([username, label]) => (
              <option value={username} key={username}>{label}</option>
            ))}
          </select>

          <p className='mt-3 text-xs text-slate-500' aria-live='polite'>
            Showing {shown.length} of {alerts.length} alerts
          </p>

          <div className='mt-6 border-t pt-4'>
            <p className='label mb-3'>Area heat</p>
            {areaHeat.slice(0, 7).map((item) => (
              <div className='mb-3' key={item.area}>
                <div className='flex justify-between text-xs'>
                  <span>{item.area}</span><b>{item.count}</b>
                </div>
                <div className='mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800'>
                  <div
                    className='h-full rounded-full bg-blue-500 transition-all'
                    style={{
                      width: Math.min(
                        100,
                        (item.count / (areaHeat[0]?.count || 1)) * 100,
                      ) + '%',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </aside>

        <section className='space-y-3'>
          <div className='card overflow-hidden'>
            <div className='border-b p-4'>
              <h2 className='font-semibold'>
                Alert inbox
                <span className='ml-2 text-sm font-normal text-slate-400'>
                  {shown.length}
                </span>
              </h2>
            </div>

            {shown.slice(0, 30).map((alert) => (
              <button
                type='button'
                onClick={() => setSelected(alert)}
                key={alert.alert_id}
                className='flex w-full items-center gap-3 border-b p-4 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/50'
              >
                <div className='min-w-0 flex-1'>
                  <p className='truncate text-sm font-semibold'>
                    {nice(alert.alert_type)} · {alert.provider}
                  </p>
                  <p className='mt-1 truncate text-xs text-slate-500'>
                    <MapPin size={12} className='inline' /> {alert.area} ·{' '}
                    {alert.agent_id}
                  </p>
                </div>
                <Severity value={alert.severity} />
                <Status value={alert.case_status} />
              </button>
            ))}
            {!shown.length && (
              <Empty
                title='No matching alerts'
                text='Try another area or risk level, or clear the filters.'
              />
            )}
          </div>
        </section>

        <aside className='space-y-5'>
          <div className='card p-4'>
            <p className='label'>Derived from API</p>
            <h2 className='mt-1 font-semibold'>Alerts by severity</h2>
            <SeverityChart alerts={shown} />
          </div>

          {selected ? (
            <>
              <AlertCard
                alert={selected}
                actions
                resolve
                onChanged={updateAlert}
              />
              <div className='card p-4'>
                <p className='label mb-4'>Case history</p>
                <div className='space-y-4'>
                  {(selected.case_history || []).map((history, index) => (
                    <div
                      key={index}
                      className='relative border-l-2 border-slate-200 pl-4 text-sm dark:border-slate-700'
                    >
                      <b>{nice(history.action)}</b>
                      <p className='mt-1 text-xs text-slate-500'>
                        {history.actor} ·{' '}
                        {new Date(history.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className='card'>
              <Empty
                title='Select a case'
                text='Choose an alert to review evidence and lifecycle controls.'
              />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
