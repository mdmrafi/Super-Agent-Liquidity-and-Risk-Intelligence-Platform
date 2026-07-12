import { useState } from 'react';
import {
  ArrowUp,
  Bot,
  Info,
  LoaderCircle,
  LockKeyhole,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import { providerDetails } from '../components/ui';

const languages = [['en', 'EN'], ['bn', 'বাংলা'], ['banglish', 'Banglish']];

export default function Assistant() {
  const { user } = useAuth();
  const isAgent = user.role === 'agent';
  const provider = providerDetails(user.provider);
  const hasScope = isAgent || Boolean(user.provider);
  const scope = isAgent
    ? `Agent ${user.agent_id || ''} · all provider balances`
    : user.provider
      ? `${provider.name} provider only`
      : 'Provider not assigned';
  const prompts = isAgent ? [
    'Which alerts need attention?',
    'Summarize my current liquidity risk',
    'What evidence supports the highest-confidence alert?',
  ] : [
    `Which ${provider.name} alerts need attention?`,
    `Summarize current ${provider.name} liquidity risk`,
    `What evidence supports the highest-confidence ${provider.name} alert?`,
  ];

  const [lang, setLang] = useState('en');
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState([{
    role: 'assistant',
    text: hasScope
      ? `I can explain current balances and alerts within your ${scope} access. What would you like to review?`
      : 'Your account has no provider assignment, so I cannot load operational intelligence yet.',
  }]);

  async function send(question = input) {
    if (!hasScope || !question.trim() || busy) return;
    setMessages((current) => [...current, { role: 'user', text: question }]);
    setInput('');
    setBusy(true);
    try {
      const response = await api.chat(question, lang);
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: response.answer },
      ]);
    } catch (requestError) {
      setMessages((current) => [
        ...current,
        { role: 'error', text: requestError.message },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className='mx-auto max-w-5xl'>
      <div className='mb-6 flex flex-wrap items-end justify-between gap-4'>
        <div>
          <p className='label'>Read-only intelligence</p>
          <h1 className='mt-2 text-3xl font-semibold'>AI Assistant</h1>
          <p className='mt-2 text-sm text-slate-500'>
            Ask questions about current liquidity and active risk signals.
          </p>
        </div>
        <div className='flex items-center gap-3'>
          <div className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold ${hasScope ? 'bg-white dark:bg-slate-900' : 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200'}`}>
            <LockKeyhole size={14} /> {scope}
          </div>
          <div className='flex rounded-xl border bg-white p-1 dark:bg-slate-900'>
            {languages.map(([value, label]) => (
              <button
                key={value}
                onClick={() => setLang(value)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold ${lang === value ? 'bg-ink text-white dark:bg-white dark:text-ink' : 'text-slate-500'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className={`mb-4 flex items-start gap-3 rounded-2xl border p-4 text-sm ${hasScope ? 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200' : 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-200'}`}>
        <Info size={18} className='mt-0.5 shrink-0' />
        <p>
          <b>{hasScope ? 'Read-only assistant.' : 'Provider assignment required.'}</b>{' '}
          {hasScope
            ? `Responses use only the server-authorized ${scope} scope and cannot modify a case. Verify critical decisions in the relevant command workspace.`
            : 'Chat is disabled because requesting intelligence without a provider scope could expose records outside this account.'}
        </p>
      </div>

      <section className='card flex min-h-[650px] flex-col overflow-hidden'>
        <div className='flex-1 space-y-6 overflow-y-auto p-5 sm:p-8'>
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}
            >
              {message.role !== 'user' && (
                <div className='grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-600 text-white'>
                  <Bot size={18} />
                </div>
              )}
              <div className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'rounded-tr-sm bg-ink text-white dark:bg-white dark:text-ink' : message.role === 'error' ? 'bg-rose-50 text-rose-700 dark:bg-rose-950/30' : 'rounded-tl-sm bg-slate-100 dark:bg-slate-800'}`}>
                {message.text}
              </div>
              {message.role === 'user' && (
                <div className='grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-slate-200 dark:bg-slate-700'>
                  <UserRound size={18} />
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className='flex items-center gap-3'>
              <div className='grid h-9 w-9 place-items-center rounded-xl bg-blue-600 text-white'>
                <Bot size={18} />
              </div>
              <div className='flex gap-1 rounded-2xl bg-slate-100 px-5 py-4 dark:bg-slate-800'>
                {[0, 1, 2].map((item) => (
                  <span
                    key={item}
                    className='h-2 w-2 animate-bounce rounded-full bg-slate-400'
                    style={{ animationDelay: `${item * 120}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        <div className='border-t p-4 sm:p-5'>
          <div className='mb-3 flex flex-wrap gap-2'>
            {prompts.map((prompt) => (
              <button
                key={prompt}
                disabled={!hasScope || busy}
                onClick={() => send(prompt)}
                className='rounded-full border px-3 py-1.5 text-xs text-slate-500 transition hover:border-blue-300 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-40'
              >
                <Sparkles size={12} className='mr-1 inline' />{prompt}
              </button>
            ))}
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
            className='relative'
          >
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              disabled={!hasScope}
              className='input py-4 pr-14 disabled:cursor-not-allowed disabled:opacity-60'
              placeholder={hasScope
                ? 'Ask about current alerts or balances…'
                : 'Provider assignment required before chatting'}
            />
            <button
              disabled={!hasScope || busy || !input.trim()}
              className='absolute right-2.5 top-2.5 grid h-9 w-9 place-items-center rounded-xl bg-ink text-white disabled:opacity-40 dark:bg-white dark:text-ink'
            >
              {busy
                ? <LoaderCircle size={17} className='animate-spin' />
                : <ArrowUp size={17} />}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
