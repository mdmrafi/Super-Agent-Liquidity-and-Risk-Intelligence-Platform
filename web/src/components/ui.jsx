import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

export const providerMeta = {
  bKash: { color: '#E2136E', class: 'text-bkash bg-bkash/10' },
  Nagad: { color: '#F58220', class: 'text-nagad bg-nagad/10' },
  Rocket: { color: '#7B3FF2', class: 'text-rocket bg-rocket/10' },
  Cash: { color: '#16A34A', class: 'text-cash bg-cash/10' },
};

export const money = (value) => new Intl.NumberFormat('en-BD', {
  style: 'currency',
  currency: 'BDT',
  maximumFractionDigits: 0,
}).format(value || 0).replace('BDT', '৳');

export const nice = (value = '') => value
  .replaceAll('_', ' ')
  .replace(/\b\w/g, (character) => character.toUpperCase());

export const dateTime = (value) => value
  ? new Intl.DateTimeFormat('en-BD', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
  : '—';

export function providerDetails(value) {
  const entry = Object.entries(providerMeta).find(
    ([name]) => name.toLowerCase() === String(value || '').toLowerCase(),
  );
  return entry
    ? { name: entry[0], ...entry[1] }
    : {
      name: value || 'Not assigned',
      color: '#64748B',
      class: 'text-slate-600 bg-slate-500/10',
    };
}

export function Severity({ value = 'low' }) {
  const color = {
    critical: 'bg-rose-500/10 text-rose-600',
    high: 'bg-rose-500/10 text-rose-600',
    medium: 'bg-amber-500/10 text-amber-700',
    low: 'bg-emerald-500/10 text-emerald-700',
  }[value] || 'bg-slate-500/10 text-slate-600';
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${color}`}>
      {nice(value)}
    </span>
  );
}

export function Status({ value = 'new' }) {
  return (
    <span className='inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300'>
      {value === 'resolved' ? <CheckCircle2 size={13} /> : <Clock3 size={13} />}
      {' '}{nice(value)}
    </span>
  );
}

export function Empty({ title = 'Nothing here yet', text, icon: Icon = Sparkles }) {
  return (
    <div className='grid min-h-56 place-items-center p-8 text-center'>
      <div>
        <div className='mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 dark:bg-slate-800'>
          <Icon className='text-slate-500' />
        </div>
        <h3 className='font-semibold'>{title}</h3>
        {text && <p className='mx-auto mt-2 max-w-md text-sm text-slate-500'>{text}</p>}
      </div>
    </div>
  );
}

export function LoadingCards() {
  return (
    <div className='grid gap-4 md:grid-cols-2 xl:grid-cols-4'>
      {[1, 2, 3, 4].map((item) => (
        <div key={item} className='card p-5'>
          <div className='skeleton h-4 w-24' />
          <div className='skeleton mt-6 h-8 w-32' />
          <div className='skeleton mt-4 h-3 w-20' />
        </div>
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className='card flex items-center gap-3 border-rose-200 p-4 text-sm text-rose-700'>
      <AlertTriangle size={19} />
      <span className='flex-1'>{message}</span>
      {onRetry && <button className='btn-secondary py-1.5' onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Spinner({ label = 'Working…' }) {
  return <><LoaderCircle size={16} className='animate-spin' />{label}</>;
}

export function ProviderAssignment({ provider, label = 'Assigned provider' }) {
  const details = providerDetails(provider);
  return (
    <div className='inline-flex items-center gap-3 rounded-2xl border bg-white/80 px-4 py-3 shadow-sm backdrop-blur dark:bg-slate-900/70'>
      <div
        className='grid h-9 w-9 place-items-center rounded-xl text-white shadow-sm'
        style={{ backgroundColor: details.color }}
      >
        <Building2 size={17} />
      </div>
      <div>
        <p className='label'>{label}</p>
        <p className='mt-0.5 text-sm font-semibold'>{details.name}</p>
      </div>
    </div>
  );
}

export function MissingProviderScope({ role }) {
  return (
    <div className='card overflow-hidden border-amber-200 dark:border-amber-900'>
      <div className='grid min-h-[380px] place-items-center p-8 text-center'>
        <div className='max-w-lg'>
          <div className='mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-amber-500/10 text-amber-600'>
            <ShieldAlert size={26} />
          </div>
          <p className='label mt-5'>Access scope required</p>
          <h2 className='mt-2 text-xl font-semibold'>No provider is assigned</h2>
          <p className='mt-3 text-sm leading-6 text-slate-500'>
            This {nice(role)} account cannot load operational data until an
            administrator assigns a provider. No unscoped records were requested.
          </p>
        </div>
      </div>
    </div>
  );
}
