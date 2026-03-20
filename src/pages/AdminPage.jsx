import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { conversationService } from '../services/api';

const TOKEN_STORAGE_KEY = 'beisser-ai-admin-token';

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(value || 0);
}

function formatNumber(value) {
  return new Intl.NumberFormat('en-US').format(value || 0);
}

function StatCard({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4 shadow-lg shadow-slate-950/20">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      {hint ? <p className="mt-2 text-sm text-slate-400">{hint}</p> : null}
    </div>
  );
}

export default function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || '');
  const [draftToken, setDraftToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || '');
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function loadMetrics(activeToken) {
    if (!activeToken) {
      setMetrics(null);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const data = await conversationService.getAdminMetrics(activeToken);
      setMetrics(data);
      localStorage.setItem(TOKEN_STORAGE_KEY, activeToken);
    } catch (err) {
      setMetrics(null);
      setError(err.message || 'Unable to load admin metrics');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) {
      loadMetrics(token);
    }
  }, [token]);

  const usageSummary = useMemo(() => metrics?.overview || {}, [metrics]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-3 py-5 sm:px-6 sm:py-8">
        <div className="flex flex-col gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-emerald-300">Admin Metrics</p>
            <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Usage, spend, and question trends</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              This dashboard pulls from the Pi analytics database and shows who is using the assistant, what they are asking,
              and how much the OpenAI traffic is costing over time.
            </p>
          </div>
          <Link className="text-sm text-emerald-300 hover:text-emerald-200" to="/">
            Back to chat
          </Link>
        </div>

        <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <label className="block text-sm font-medium text-slate-200">Admin token</label>
          <div className="mt-3 flex flex-col gap-3 md:flex-row">
            <input
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none ring-0 placeholder:text-slate-500"
              placeholder="Paste admin token"
              value={draftToken}
              onChange={(event) => setDraftToken(event.target.value)}
              type="password"
            />
            <button
              className="w-full rounded-xl bg-emerald-500 px-4 py-3 text-sm font-medium text-white hover:bg-emerald-400 md:w-auto"
              onClick={() => setToken(draftToken.trim())}
            >
              Load dashboard
            </button>
            <button
              className="w-full rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-200 hover:bg-slate-800 md:w-auto"
              onClick={() => {
                localStorage.removeItem(TOKEN_STORAGE_KEY);
                setDraftToken('');
                setToken('');
                setMetrics(null);
                setError('');
              }}
            >
              Clear token
            </button>
          </div>
          {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}
          {metrics?.generatedAt ? <p className="mt-3 text-xs text-slate-500">Updated {metrics.generatedAt}</p> : null}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Spend Today" value={formatCurrency(usageSummary.spendToday)} hint={`${formatNumber(usageSummary.questionsToday)} questions today`} />
          <StatCard label="Spend This Month" value={formatCurrency(usageSummary.spendMonth)} hint={`${formatNumber(usageSummary.questions30d)} questions in the last 30 days`} />
          <StatCard label="Spend This Year" value={formatCurrency(usageSummary.spendYear)} hint={`${formatNumber(usageSummary.activeUsers30d)} active users in 30 days`} />
          <StatCard
            label="Cache Hit Rate"
            value={`${((usageSummary.cacheHitRate30d || 0) * 100).toFixed(1)}%`}
            hint={`${formatNumber(usageSummary.inputTokensTotal)} input / ${formatNumber(usageSummary.outputTokensTotal)} output tokens`}
          />
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-xl font-semibold">Trending questions</h2>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Top repeated asks</p>
            </div>
            <div className="mt-4 space-y-3">
              {(metrics?.topQuestions || []).map((item) => (
                <div key={`${item.question}-${item.lastAskedAt}`} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-sm font-medium text-white">{item.question}</p>
                  <p className="mt-2 text-xs text-slate-400">
                    {formatNumber(item.count)} asks across {formatNumber(item.users)} users
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Last asked {item.lastAskedAt}</p>
                </div>
              ))}
              {!loading && (metrics?.topQuestions || []).length === 0 ? (
                <p className="text-sm text-slate-400">No ask analytics yet.</p>
              ) : null}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-xl font-semibold">Feedback signals</h2>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Engagement events</p>
            </div>
            <div className="mt-4 space-y-3">
              {(metrics?.feedbackSummary || []).map((item) => (
                <div key={item.eventType} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3">
                  <span className="text-sm text-slate-200">{item.eventType}</span>
                  <span className="text-sm font-semibold text-white">{formatNumber(item.count)}</span>
                </div>
              ))}
              {!loading && (metrics?.feedbackSummary || []).length === 0 ? (
                <p className="text-sm text-slate-400">No engagement feedback has been recorded yet.</p>
              ) : null}
            </div>
          </section>
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-xl font-semibold">User cost breakdown</h2>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">By account</p>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-slate-400">
                  <tr className="border-b border-slate-800">
                    <th className="px-3 py-2 font-medium">User</th>
                    <th className="px-3 py-2 font-medium">Questions</th>
                    <th className="px-3 py-2 font-medium">Spend</th>
                    <th className="px-3 py-2 font-medium">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {(metrics?.topUsers || []).map((item) => (
                    <tr key={item.userIdentity} className="border-b border-slate-900 align-top text-slate-200">
                      <td className="px-3 py-3">
                        <div className="font-medium text-white">{item.userIdentity}</div>
                        <div className="mt-1 text-xs text-slate-500">{item.lastAskedAt || 'No activity yet'}</div>
                      </td>
                      <td className="px-3 py-3">{formatNumber(item.questionCount)}</td>
                      <td className="px-3 py-3">{formatCurrency(item.totalCostUsd)}</td>
                      <td className="px-3 py-3 text-xs text-slate-400">
                        In {formatNumber(item.inputTokens)}
                        <br />
                        Out {formatNumber(item.outputTokens)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!loading && (metrics?.topUsers || []).length === 0 ? (
                <p className="mt-3 text-sm text-slate-400">No user activity has been recorded yet.</p>
              ) : null}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-xl font-semibold">30-day usage</h2>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Daily rollup</p>
            </div>
            <div className="mt-4 space-y-3">
              {(metrics?.usageByDay || []).map((item) => (
                <div key={item.day} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <div className="flex items-center justify-between text-sm text-white">
                    <span>{item.day}</span>
                    <span>{formatCurrency(item.totalCostUsd)}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                    <span>{formatNumber(item.questionCount)} questions</span>
                    <span>{formatNumber(item.cacheHits)} cache hits</span>
                  </div>
                </div>
              ))}
              {!loading && (metrics?.usageByDay || []).length === 0 ? (
                <p className="text-sm text-slate-400">No daily analytics have been recorded yet.</p>
              ) : null}
            </div>
          </section>
        </div>

        <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-xl font-semibold">Recent feedback activity</h2>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Latest events</p>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-800">
                  <th className="px-3 py-2 font-medium">When</th>
                  <th className="px-3 py-2 font-medium">User</th>
                  <th className="px-3 py-2 font-medium">Event</th>
                  <th className="px-3 py-2 font-medium">Label</th>
                </tr>
              </thead>
              <tbody>
                {(metrics?.recentFeedback || []).map((item, index) => (
                  <tr key={`${item.createdAt}-${item.eventType}-${index}`} className="border-b border-slate-900 text-slate-200">
                    <td className="px-3 py-3 text-xs text-slate-400">{item.createdAt}</td>
                    <td className="px-3 py-3">{item.userIdentity}</td>
                    <td className="px-3 py-3">{item.eventType}</td>
                    <td className="px-3 py-3 text-slate-400">{item.label || 'n/a'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && (metrics?.recentFeedback || []).length === 0 ? (
              <p className="mt-3 text-sm text-slate-400">No recent feedback events yet.</p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
