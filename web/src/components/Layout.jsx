import {
  Bot,
  Building2,
  Command,
  LogOut,
  Menu,
  Moon,
  Radar,
  ShieldCheck,
  Sun,
  WalletCards,
  X,
} from 'lucide-react';
import { NavLink, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { nice, providerDetails } from './ui';

const roleItems = {
  agent: [['/cockpit', 'Agent Cockpit', WalletCards]],
  field_officer: [['/network', 'Network Command', Command]],
  provider_ops: [['/provider', 'Provider Command', Building2]],
  risk_team: [['/risk', 'Risk Intelligence', ShieldCheck]],
};

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [dark, setDark] = useState(() => localStorage.theme === 'dark'
    || (!('theme' in localStorage)
      && matchMedia('(prefers-color-scheme: dark)').matches));
  const location = useLocation();
  const provider = providerDetails(user.provider);
  const isAgent = user.role === 'agent';
  const scopeLabel = isAgent
    ? `Agent ${user.agent_id || ''} · All providers`
    : user.provider
      ? `${provider.name} provider`
      : 'Provider not assigned';

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.theme = dark ? 'dark' : 'light';
  }, [dark]);

  const nav = [
    ...(roleItems[user.role] || []),
    ['/assistant', 'AI Assistant', Bot],
  ];

  return (
    <div className='min-h-screen'>
      <aside className={`fixed inset-y-0 left-0 z-50 w-72 border-r bg-ink px-4 py-5 text-white transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className='flex items-center justify-between px-2'>
          <div className='flex items-center gap-3'>
            <div className='grid h-10 w-10 place-items-center rounded-2xl bg-blue-500'>
              <Radar />
            </div>
            <div>
              <b>Super Agent</b>
              <p className='text-xs text-slate-400'>MFS intelligence</p>
            </div>
          </div>
          <button className='lg:hidden' onClick={() => setOpen(false)}>
            <X />
          </button>
        </div>

        <nav className='mt-10 space-y-1'>
          {nav.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${isActive ? 'bg-white text-ink' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
            >
              <Icon size={19} />{label}
            </NavLink>
          ))}
        </nav>

        <div className='absolute inset-x-4 bottom-5 rounded-2xl border border-white/10 bg-white/5 p-3'>
          <div className='mb-3 flex items-start gap-3'>
            <div
              className='grid h-9 w-9 shrink-0 place-items-center rounded-xl font-bold text-white'
              style={{ backgroundColor: isAgent ? '#3B82F6' : provider.color }}
            >
              {(user.display_name || user.username)[0]}
            </div>
            <div className='min-w-0'>
              <p className='truncate text-sm font-semibold'>
                {user.display_name || user.username}
              </p>
              <p className='truncate text-xs text-slate-400'>{nice(user.role)}</p>
              <p className={`mt-1 truncate text-xs ${!isAgent && !user.provider ? 'text-amber-300' : 'text-blue-300'}`}>
                {scopeLabel}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className='flex w-full items-center gap-2 rounded-lg px-2 py-2 text-xs text-slate-400 hover:bg-white/5 hover:text-white'
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <div className='lg:pl-72'>
        <header className='sticky top-0 z-40 flex h-16 items-center justify-between border-b bg-white/75 px-4 backdrop-blur-xl dark:bg-slate-950/75 sm:px-7'>
          <button onClick={() => setOpen(true)} className='lg:hidden'>
            <Menu />
          </button>
          <div className='hidden sm:block'>
            <p className='text-sm font-semibold'>Operational control center</p>
            <p className='text-xs text-slate-500'>
              {scopeLabel} · API-enforced access
            </p>
          </div>
          <button
            onClick={() => setDark(!dark)}
            className='grid h-9 w-9 place-items-center rounded-xl border hover:bg-slate-50 dark:hover:bg-slate-900'
            aria-label='Toggle dark mode'
          >
            {dark ? <Sun size={17} /> : <Moon size={17} />}
          </button>
        </header>
        <main className='mx-auto max-w-[1600px] p-4 sm:p-7'>{children}</main>
      </div>
    </div>
  );
}
