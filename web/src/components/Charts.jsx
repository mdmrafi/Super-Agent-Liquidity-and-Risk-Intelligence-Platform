import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { providerMeta } from './ui';

const tip = {
  contentStyle: {
    borderRadius: 12,
    border: '1px solid #e2e8f0',
    fontSize: 12,
  },
};

const historySeries = [
  { key: 'cash', asOfKey: 'cashAsOf', label: 'Physical Cash', color: providerMeta.Cash.color },
  { key: 'bKash', asOfKey: 'bKashAsOf', label: 'bKash', color: providerMeta.bKash.color },
  { key: 'Nagad', asOfKey: 'NagadAsOf', label: 'Nagad', color: providerMeta.Nagad.color },
  { key: 'Rocket', asOfKey: 'RocketAsOf', label: 'Rocket', color: providerMeta.Rocket.color },
];

const numberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const providerReading = (readings, provider) => {
  const entry = Object.entries(readings || {}).find(
    ([name]) => name.toLowerCase() === provider.toLowerCase(),
  );
  return entry?.[1] || null;
};

const formatAxisTime = (value) => new Intl.DateTimeFormat('en-BD', {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}).format(new Date(value));

const formatDateTime = (value) => value
  ? new Intl.DateTimeFormat('en-BD', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
  : 'Not recorded';

const formatCompactBalance = (value) => new Intl.NumberFormat('en-BD', {
  notation: 'compact',
  maximumFractionDigits: 1,
}).format(value);

const formatBalance = (value) => `BDT ${new Intl.NumberFormat('en-BD', {
  maximumFractionDigits: 0,
}).format(value)}`;

export function buildHistoricalSeries(buckets = [], windowMinutes = 30) {
  const interval = Math.max(Number(windowMinutes) || 30, 1) * 60 * 1000;
  const points = buckets
    .map((bucket) => {
      const timestamp = Date.parse(bucket.bucket_start);
      if (!Number.isFinite(timestamp)) return null;

      const bKash = providerReading(bucket.provider_closing_balances, 'bKash');
      const Nagad = providerReading(bucket.provider_closing_balances, 'Nagad');
      const Rocket = providerReading(bucket.provider_closing_balances, 'Rocket');

      return {
        timestamp,
        bucketStart: bucket.bucket_start,
        bucketEnd: bucket.bucket_end,
        transactionCount: numberOrNull(bucket.transaction_count),
        cash: numberOrNull(bucket.cash_closing_balance),
        cashAsOf: bucket.cash_as_of || null,
        bKash: numberOrNull(bKash?.balance),
        bKashAsOf: bKash?.as_of || null,
        Nagad: numberOrNull(Nagad?.balance),
        NagadAsOf: Nagad?.as_of || null,
        Rocket: numberOrNull(Rocket?.balance),
        RocketAsOf: Rocket?.as_of || null,
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.timestamp - right.timestamp);

  // An explicit null point prevents Recharts from drawing across an omitted
  // ledger window. It represents missing data, never an estimated balance.
  return points.flatMap((point, index) => {
    const previous = points[index - 1];
    if (!previous || point.timestamp - previous.timestamp <= interval * 1.5) return [point];
    return [{
      timestamp: previous.timestamp + interval,
      bucketStart: new Date(previous.timestamp + interval).toISOString(),
      bucketEnd: new Date(previous.timestamp + interval * 2).toISOString(),
      transactionCount: null,
      cash: null,
      cashAsOf: null,
      bKash: null,
      bKashAsOf: null,
      Nagad: null,
      NagadAsOf: null,
      Rocket: null,
      RocketAsOf: null,
      isGap: true,
    }, point];
  });
}

function HistoricalTooltip({ active, payload }) {
  const point = payload?.[0]?.payload;
  if (!active || !point || point.isGap) return null;

  return (
    <div className='max-w-xs rounded-xl border bg-white/95 p-3 text-xs shadow-xl backdrop-blur dark:bg-slate-950/95'>
      <p className='font-semibold text-slate-900 dark:text-slate-100'>
        {formatDateTime(point.bucketStart)}
      </p>
      <p className='mt-0.5 text-[11px] text-slate-500'>
        Window ends {formatDateTime(point.bucketEnd)}
      </p>
      <div className='my-2.5 border-t' />
      <div className='space-y-2'>
        {historySeries.map((series) => (
          <div key={series.key} className='flex items-start gap-2'>
            <span
              className='mt-1 h-2 w-2 shrink-0 rounded-full'
              style={{ backgroundColor: series.color }}
            />
            <div className='min-w-0 flex-1'>
              <div className='flex justify-between gap-4'>
                <span className='text-slate-500'>{series.label}</span>
                <span className='font-semibold'>
                  {point[series.key] === null ? 'No reading' : formatBalance(point[series.key])}
                </span>
              </div>
              {point[series.asOfKey] && (
                <p className='mt-0.5 text-[10px] text-slate-400'>
                  Ledger as of {formatDateTime(point[series.asOfKey])}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className='mt-2.5 flex justify-between border-t pt-2 text-slate-500'>
        <span>Ledger observations in window</span>
        <span className='font-semibold text-slate-700 dark:text-slate-200'>
          {point.transactionCount ?? 'Not recorded'}
        </span>
      </div>
    </div>
  );
}

export function HistoricalBalanceChart({ buckets, windowMinutes = 30 }) {
  const data = buildHistoricalSeries(buckets, windowMinutes);
  if (!data.length) {
    return (
      <div className='grid h-[320px] place-items-center px-6 text-center text-sm text-slate-500'>
        Ledger buckets were returned, but none contained a valid timestamp to plot.
      </div>
    );
  }
  const timestamps = data.map((point) => point.timestamp);
  const interval = Math.max(Number(windowMinutes) || 30, 1) * 60 * 1000;
  let minimum = Math.min(...timestamps);
  let maximum = Math.max(...timestamps);
  if (minimum === maximum) {
    minimum -= interval / 2;
    maximum += interval / 2;
  }

  return (
    <ResponsiveContainer width='100%' height={320}>
      <LineChart data={data} margin={{ top: 14, right: 14, left: 6, bottom: 10 }}>
        <CartesianGrid strokeDasharray='3 3' vertical={false} opacity={0.24} />
        <XAxis
          dataKey='timestamp'
          type='number'
          scale='time'
          domain={[minimum, maximum]}
          tickFormatter={formatAxisTime}
          tickLine={false}
          axisLine={false}
          minTickGap={44}
          tick={{ fontSize: 11, fill: '#64748b' }}
        />
        <YAxis
          tickFormatter={formatCompactBalance}
          tickLine={false}
          axisLine={false}
          width={52}
          tick={{ fontSize: 11, fill: '#64748b' }}
        />
        <Tooltip content={<HistoricalTooltip />} />
        <Legend iconType='circle' wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        {historySeries.map((series) => (
          <Line
            key={series.key}
            type='linear'
            dataKey={series.key}
            name={series.label}
            stroke={series.color}
            strokeWidth={2.25}
            dot={series.key === 'cash' ? false : { r: 2.25, strokeWidth: 0 }}
            activeDot={{ r: 4, strokeWidth: 2 }}
            connectNulls={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function BalanceChart({ data }) {
  return (
    <ResponsiveContainer width='100%' height={250}>
      <PieChart>
        <Pie data={data} dataKey='value' nameKey='name' innerRadius={65} outerRadius={92} paddingAngle={4}>
          {data.map((item) => (
            <Cell key={item.name} fill={providerMeta[item.name]?.color || '#64748b'} />
          ))}
        </Pie>
        <Tooltip {...tip} />
        <Legend iconType='circle' />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function SeverityChart({ alerts }) {
  const keys = ['critical', 'high', 'medium', 'low'];
  const data = keys.map((name) => ({
    name: name[0].toUpperCase() + name.slice(1),
    count: alerts.filter((alert) => alert.severity === name).length,
  }));
  return (
    <ResponsiveContainer width='100%' height={260}>
      <BarChart data={data} margin={{ top: 10, right: 8, left: -22, bottom: 0 }}>
        <CartesianGrid strokeDasharray='3 3' vertical={false} opacity={0.25} />
        <XAxis dataKey='name' tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
        <Tooltip {...tip} />
        <Bar dataKey='count' fill='#2563eb' radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ProviderChart({ alerts }) {
  const data = ['bKash', 'Nagad', 'Rocket'].map((name) => ({
    name,
    count: alerts.filter((alert) => alert.provider?.toLowerCase() === name.toLowerCase()).length,
    color: providerMeta[name].color,
  }));
  return (
    <ResponsiveContainer width='100%' height={260}>
      <BarChart data={data} layout='vertical' margin={{ left: 8 }}>
        <CartesianGrid strokeDasharray='3 3' horizontal={false} opacity={0.25} />
        <XAxis type='number' allowDecimals={false} axisLine={false} />
        <YAxis type='category' dataKey='name' axisLine={false} tickLine={false} />
        <Tooltip {...tip} />
        <Bar dataKey='count' radius={[0, 8, 8, 0]}>
          {data.map((item) => <Cell key={item.name} fill={item.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
