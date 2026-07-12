import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Banknote,
  Database,
  RefreshCw,
  WalletCards,
} from 'lucide-react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { BalanceChart, HistoricalBalanceChart } from '../components/Charts';
import AlertCard from '../components/AlertCard';
import {
  Empty,
  ErrorState,
  LoadingCards,
  money,
  providerMeta,
} from '../components/ui';

const ANALYTICS_WINDOW_MINUTES = 30;
const ANALYTICS_LIMIT = 96;

export default function AgentCockpit() {
  const { user } = useAuth();
  const [balances, setBalances] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [error, setError] = useState('');
  const [analyticsError, setAnalyticsError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setAnalyticsLoading(true);
    setError('');
    setAnalyticsError('');

    const analyticsRequest = api.analytics(user.agent_id, {
      windowMinutes: ANALYTICS_WINDOW_MINUTES,
      limit: ANALYTICS_LIMIT,
    }).then((data) => ({ data })).catch((requestError) => ({ requestError }));

    try {
      const [balanceData, alertData, analyticsResult] = await Promise.all([
        api.balances(user.agent_id),
        api.alerts({ agent_id: user.agent_id, audience: 'agent' }),
        analyticsRequest,
      ]);
      setBalances(balanceData);
      setAlerts(alertData);

      if (analyticsResult.requestError) {
        setAnalytics(null);
        setAnalyticsError(analyticsResult.requestError.message);
      } else {
        setAnalytics(analyticsResult.data);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
      setAnalyticsLoading(false);
    }
  }, [user.agent_id]);

  const retryAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    setAnalyticsError('');
    try {
      const data = await api.analytics(user.agent_id, {
        windowMinutes: ANALYTICS_WINDOW_MINUTES,
        limit: ANALYTICS_LIMIT,
      });
      setAnalytics(data);
    } catch (requestError) {
      setAnalytics(null);
      setAnalyticsError(requestError.message);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [user.agent_id]);

  useEffect(() => {
    load();
  }, [load]);

  const balanceDistribution = useMemo(() => {
    if (!balances) return [];
    return [
      { name: 'Cash', value: balances.cash },
      ...Object.entries(balances.providers || {}).map(([name, reading]) => ({
        name,
        value: reading.balance,
      })),
    ].filter((item) => item.value !== null && item.value !== undefined);
  }, [balances]);

  if (loading) return <><Title /><LoadingCards /></>;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const items = [
    {
      name: 'Cash',
      label: 'Physical Cash',
      balance: balances.cash,
      asOf: balances.cash_as_of,
    },
    ...['bKash', 'Nagad', 'Rocket'].map((name) => ({
      name,
      label: name,
      balance: balances.providers?.[name]?.balance,
      asOf: balances.providers?.[name]?.as_of,
    })),
  ];
  const buckets = Array.isArray(analytics?.buckets) ? analytics.buckets : [];
  const windowMinutes = analytics?.window_minutes || ANALYTICS_WINDOW_MINUTES;

  return (
    <div className='space-y-7'>
      <Title area={balances.area} />

      <section className='grid gap-4 sm:grid-cols-2 xl:grid-cols-4'>
        {items.map((item) => {
          const activeAlerts = alerts.filter((alert) => (
            item.name === 'Cash'
              ? !alert.provider
              : alert.provider?.toLowerCase() === item.name.toLowerCase()
          ) && alert.case_status !== 'resolved');
          const atRisk = activeAlerts.length > 0;
          return (
            <div className='card p-5' key={item.name}>
              <div className='flex items-center justify-between'>
                <div className={`grid h-10 w-10 place-items-center rounded-xl ${providerMeta[item.name]?.class}`}>
                  <WalletCards size={19} />
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${atRisk ? 'bg-rose-500/10 text-rose-600' : 'bg-emerald-500/10 text-emerald-700'}`}>
                  {atRisk ? 'At risk' : 'Normal'}
                </span>
              </div>
              <p className='mt-5 text-sm text-slate-500'>{item.label}</p>
              <p className='mt-1 text-2xl font-semibold'>
                {item.balance == null ? 'Unavailable' : money(item.balance)}
              </p>
              <p className='mt-4 text-xs text-slate-400'>
                {atRisk
                  ? `${Math.max(...activeAlerts.map((alert) => Math.round(alert.confidence * 100)))}% confidence`
                  : `Latest snapshot · ${item.asOf ? new Date(item.asOf).toLocaleTimeString('en-BD', { hour: '2-digit', minute: '2-digit' }) : '—'}`}
              </p>
            </div>
          );
        })}
      </section>

      <section className='grid gap-5 xl:grid-cols-3'>
        <div className='card p-5 xl:col-span-1'>
          <div className='mb-2 flex items-center justify-between'>
            <div>
              <p className='label'>Current snapshot</p>
              <h2 className='mt-1 text-lg font-semibold'>Balance distribution</h2>
            </div>
            <Activity className='text-slate-400' />
          </div>
          <BalanceChart data={balanceDistribution} />
        </div>

        <div className='card overflow-hidden xl:col-span-2'>
          <div className='flex flex-wrap items-center justify-between gap-3 border-b p-5'>
            <div>
              <p className='label'>30-minute operational analytics</p>
              <h2 className='mt-1 text-lg font-semibold'>Historical balances</h2>
            </div>
            <div className='flex items-center gap-2'>
              {buckets.length > 0 && !analyticsLoading && !analyticsError && (
                <span className='inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-700 dark:border-emerald-900 dark:text-emerald-400'>
                  <Database size={13} />
                  Actual ledger · {windowMinutes}m buckets
                </span>
              )}
              <button
                type='button'
                className='btn-secondary px-3 py-1.5 text-xs'
                onClick={retryAnalytics}
                disabled={analyticsLoading}
                aria-label='Refresh historical analytics'
                title='Refresh historical analytics'
              >
                <RefreshCw size={13} className={analyticsLoading ? 'animate-spin' : ''} />
                <span className='hidden sm:inline'>Refresh</span>
              </button>
            </div>
          </div>

          {analyticsLoading ? (
            <div className='p-5'>
              <div className='skeleton h-[320px] w-full' />
            </div>
          ) : analyticsError ? (
            <div className='p-5'>
              <ErrorState
                message={`Historical analytics could not be loaded: ${analyticsError}`}
                onRetry={retryAnalytics}
              />
            </div>
          ) : buckets.length > 0 ? (
            <div className='px-3 pb-4 pt-2 sm:px-5'>
              <HistoricalBalanceChart buckets={buckets} windowMinutes={windowMinutes} />
              <p className='px-2 text-xs leading-5 text-slate-500'>
                Closing balances are plotted only when a ledger reading exists. Missing windows remain visible as gaps and are never estimated.
              </p>
            </div>
          ) : (
            <Empty
              icon={BarChart3}
              title='Analytics coming soon'
              text='No 30-minute ledger buckets are available yet. Current balances and active intelligence signals are shown instead—no historical data has been fabricated.'
            />
          )}
        </div>
      </section>

      <section>
        <div className='mb-4 flex items-end justify-between'>
          <div>
            <p className='label'>Live intelligence</p>
            <h2 className='mt-1 text-xl font-semibold'>Alerts</h2>
          </div>
          <span className='text-sm text-slate-500'>{alerts.length} signals</span>
        </div>
        <div className='grid gap-4 xl:grid-cols-2'>
          {alerts.length
            ? alerts.map((alert) => <AlertCard key={alert.alert_id} alert={alert} />)
            : <Empty title='No active signals' text='The current API response contains no alerts for this agent.' />}
        </div>
      </section>
    </div>
  );
}

function Title({ area }) {
  return (
    <div className='flex flex-wrap items-end justify-between gap-4'>
      <div>
        <p className='label'>Agent cockpit</p>
        <h1 className='mt-2 text-3xl font-semibold tracking-tight'>Your liquidity, at a glance</h1>
        <p className='mt-2 text-sm text-slate-500'>{area || 'Loading operational snapshot…'}</p>
      </div>
      <div className='flex items-center gap-2 rounded-xl border bg-white px-3 py-2 text-xs text-slate-500 dark:bg-slate-900'>
        <Banknote size={16} /> Live snapshot <ArrowUpRight size={14} />
      </div>
    </div>
  );
}
