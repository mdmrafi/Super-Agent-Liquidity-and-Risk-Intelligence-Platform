import { useState } from 'react';
import {
  ArrowRight,
  Building2,
  Command,
  Eye,
  EyeOff,
  LoaderCircle,
  Radar,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const roles = [
  { value: 'agent', Icon: UserRound, title: 'Agent', text: 'Monitor all provider balances' },
  { value: 'field_officer', Icon: Command, title: 'Field officer', text: 'Coordinate assigned provider cases' },
  { value: 'provider_ops', Icon: Building2, title: 'Provider ops', text: 'Manage assigned provider e-money' },
  { value: 'risk_team', Icon: ShieldCheck, title: 'Risk team', text: 'Review assigned provider intelligence' },
];

const homes = {
  agent: '/cockpit',
  field_officer: '/network',
  provider_ops: '/provider',
  risk_team: '/risk',
};

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    role: '',
    username: '',
    password: '',
    remember: true,
  });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const selectedRole = roles.find((role) => role.value === form.role);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const user = await login(
        form.username,
        form.password,
        form.role,
        form.remember,
      );
      nav(homes[user.role] || '/assistant', { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className='grid min-h-screen bg-white dark:bg-slate-950 lg:grid-cols-[1.05fr_.95fr]'>
      <section className='relative hidden overflow-hidden bg-ink p-12 text-white lg:flex lg:flex-col lg:justify-between'>
        <div className='absolute -right-32 top-10 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl' />
        <div className='absolute -bottom-24 left-0 h-80 w-80 rounded-full bg-purple-500/20 blur-3xl' />
        <div className='relative flex items-center gap-3'>
          <div className='grid h-11 w-11 place-items-center rounded-2xl bg-blue-500'>
            <Radar />
          </div>
          <b className='text-xl'>Super Agent</b>
        </div>
        <div className='relative max-w-xl'>
          <p className='label text-blue-300'>Bangladesh MFS intelligence</p>
          <h1 className='mt-5 text-5xl font-semibold leading-[1.08] tracking-tight'>
            Clarity for every taka in motion.
          </h1>
          <p className='mt-5 max-w-lg text-lg leading-8 text-slate-400'>
            A unified control center for physical cash and provider e-money
            risk—built for decisions grounded in evidence.
          </p>
          <div className='mt-12 grid grid-cols-2 gap-3'>
            {roles.map(({ Icon, title, text }, index) => (
              <div
                key={title}
                className='animate-float rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur'
                style={{ animationDelay: `${index * 0.5}s` }}
              >
                <Icon size={20} className='text-blue-300' />
                <p className='mt-3 text-sm font-semibold'>{title}</p>
                <p className='mt-1 text-xs text-slate-400'>{text}</p>
              </div>
            ))}
          </div>
        </div>
        <p className='relative text-xs text-slate-500'>
          Secure role and provider access · API-derived intelligence
        </p>
      </section>

      <section className='flex items-center justify-center p-6 sm:p-12'>
        <div className='w-full max-w-md'>
          <div className='mb-10 flex items-center gap-3 lg:hidden'>
            <div className='grid h-10 w-10 place-items-center rounded-2xl bg-blue-600 text-white'>
              <Radar />
            </div>
            <b>Super Agent</b>
          </div>
          <p className='label'>Welcome back</p>
          <h2 className='mt-3 text-3xl font-semibold tracking-tight'>
            Sign in to your workspace
          </h2>
          <p className='mt-2 text-sm text-slate-500'>
            Select your role. Your provider assignment is verified from your account.
          </p>

          <form onSubmit={submit} className='mt-8 space-y-5'>
            <label className='block text-sm font-medium' htmlFor='role'>
              Role
              <select
                id='role'
                required
                className='input mt-2'
                value={form.role}
                onChange={(event) => setForm({ ...form, role: event.target.value })}
              >
                <option value='' disabled>Select your role</option>
                {roles.map((role) => (
                  <option value={role.value} key={role.value}>{role.title}</option>
                ))}
              </select>
            </label>

            {selectedRole && (
              <div className='flex items-center gap-3 rounded-xl border bg-slate-50 px-3 py-2.5 text-xs text-slate-600 dark:bg-slate-900 dark:text-slate-300'>
                <selectedRole.Icon size={17} className='text-blue-600' />
                <span>{selectedRole.text}</span>
              </div>
            )}

            <label className='block text-sm font-medium' htmlFor='username'>
              Username
              <input
                id='username'
                required
                autoComplete='username'
                className='input mt-2'
                value={form.username}
                onChange={(event) => setForm({ ...form, username: event.target.value })}
                placeholder='Enter your username'
              />
            </label>

            <label className='block text-sm font-medium' htmlFor='password'>
              Password
              <div className='relative mt-2'>
                <input
                  id='password'
                  required
                  autoComplete='current-password'
                  type={show ? 'text' : 'password'}
                  className='input pr-12'
                  value={form.password}
                  onChange={(event) => setForm({ ...form, password: event.target.value })}
                  placeholder='Enter your password'
                />
                <button
                  type='button'
                  onClick={() => setShow(!show)}
                  className='absolute right-3 top-3 text-slate-400'
                  aria-label={show ? 'Hide password' : 'Show password'}
                >
                  {show ? <EyeOff size={19} /> : <Eye size={19} />}
                </button>
              </div>
            </label>

            <label className='flex items-center gap-2 text-sm text-slate-600'>
              <input
                type='checkbox'
                checked={form.remember}
                onChange={(event) => setForm({ ...form, remember: event.target.checked })}
                className='rounded'
              />
              Remember me
            </label>

            {error && (
              <div className='rounded-xl bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/30'>
                {error}
              </div>
            )}

            <button disabled={busy} className='btn-primary w-full py-3.5'>
              {busy ? (
                <><LoaderCircle size={18} className='animate-spin' /> Signing in…</>
              ) : (
                <>Continue <ArrowRight size={18} /></>
              )}
            </button>
          </form>
          <p className='mt-8 text-center text-xs text-slate-400'>
            Protected by bearer-token authentication
          </p>
        </div>
      </section>
    </div>
  );
}
