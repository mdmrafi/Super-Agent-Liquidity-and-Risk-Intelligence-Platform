import { useCallback, useEffect, useMemo, useState } from 'react';
import { Building2, CheckCircle2 } from 'lucide-react';
import { api } from '../api';
import { SeverityChart } from '../components/Charts';
import AlertCard from '../components/AlertCard';
import { useAuth } from '../context/AuthContext';
import {
  Empty,
  ErrorState,
  LoadingCards,
  MissingProviderScope,
  ProviderAssignment,
  providerDetails,
} from '../components/ui';

const normalize = (value) => String(value || '').trim().toLowerCase();

export default function ProviderCommand() {
  const { user } = useAuth();
  const provider = user.provider;
  const providerStyle = providerDetails(provider);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    if (!provider) {
      setAlerts([]);
      setLoading(false);
      return;
    }
    try {
      const response = await api.alerts({
        audience: 'provider_ops',
        provider,
      });
      setAlerts(response.filter((alert) =>
        alert.liquidity_type === 'provider_emoney'
        && normalize(alert.provider) === normalize(provider)));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    load();
  }, [load]);

  const active = useMemo(
    () => alerts.filter((alert) => alert.case_status !== 'resolved'),
    [alerts],
  );
  const averageConfidence = active.length
    ? Math.round(active.reduce(
      (sum, alert) => sum + Number(alert.confidence || 0),
      0,
    ) / active.length * 100)
    : 0;

  const update = (updated) => setAlerts((current) => current.map((alert) =>
    alert.alert_id === updated.alert_id ? updated : alert));

  if (!provider) {
    return (
      <div className='space-y-6'>
        <div>
          <p className='label'>Provider operations</p>
          <h1 className='mt-2 text-3xl font-semibold'>Provider Command</h1>
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
          <p className='label'>Provider operations</p>
          <h1 className='mt-2 text-3xl font-semibold'>Provider Command</h1>
          <p className='mt-2 text-sm text-slate-500'>
            {provider} e-money intelligence only. Physical cash and other
            providers are excluded from this workspace.
          </p>
        </div>
        <ProviderAssignment provider={provider} />
      </div>

      {error && <ErrorState message={error} onRetry={load} />}

      <section className='grid gap-4 md:grid-cols-3'>
        <Metric label='Active cases' value={active.length} color={providerStyle.color} />
        <Metric label='Average confidence' value={`${averageConfidence}%`} />
        <Metric
          label='Resolved cases'
          value={alerts.filter((alert) => alert.case_status === 'resolved').length}
        />
      </section>

      <section className='grid gap-5 xl:grid-cols-[1.1fr_.9fr]'>
        <div>
          <div className='mb-4'>
            <p className='label'>Operations inbox</p>
            <h2 className='mt-1 text-xl font-semibold'>{provider} e-money issues</h2>
          </div>
          <div className='space-y-4'>
            {alerts.length ? alerts.slice(0, 20).map((alert) => (
              <AlertCard
                key={alert.alert_id}
                alert={alert}
                actions
                onChanged={update}
              />
            )) : (
              <div className='card'>
                <Empty
                  icon={CheckCircle2}
                  title='No provider issues'
                  text={`The current API response contains no ${provider} e-money cases.`}
                />
              </div>
            )}
          </div>
        </div>

        <div className='space-y-5'>
          <div className='card p-5'>
            <p className='label'>Derived from scoped API response</p>
            <h2 className='mt-1 text-lg font-semibold'>Active alerts by severity</h2>
            <p className='mt-1 text-xs text-slate-500'>
              Statistical view of {provider} alerts only
            </p>
            <SeverityChart alerts={active} />
          </div>

          <div className='card p-5'>
            <div className='flex items-center gap-2'>
              <Building2 size={18} />
              <h2 className='font-semibold'>{provider} performance summary</h2>
            </div>
            <dl className='mt-5 space-y-4 text-sm'>
              {['new', 'acknowledged', 'escalated'].map((status) => (
                <div className='flex justify-between' key={status}>
                  <dt className='capitalize text-slate-500'>{status}</dt>
                  <dd className='font-semibold'>
                    {alerts.filter((alert) => alert.case_status === status).length}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, color }) {
  return (
    <div className='card relative overflow-hidden p-5'>
      {color && <div className='absolute inset-x-0 top-0 h-1' style={{ backgroundColor: color }} />}
      <p className='label'>{label}</p>
      <p className='mt-3 text-3xl font-semibold'>{value}</p>
    </div>
  );
}
