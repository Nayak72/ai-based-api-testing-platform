import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Card, Button, Modal } from '../components/ui'
import { sessionsApi, Session } from '../api/endpoints'
import { useSSE } from '../hooks/useSSE'
import {
  Cpu,
  CheckCircle,
  WarningCircle,
  XCircle,
  Clock,
  ShieldCheck,
  FileText,
  ThumbsUp,
  ThumbsDown,
  Lightning,
} from '@phosphor-icons/react'
import toast from 'react-hot-toast'

const AGENT_STEPS = [
  { id: 'ingest', stage: 'ingest', name: 'Ingest & Index', desc: 'Parses OpenAPI spec and indexes RAG vector chunks' },
  { id: 'planner', stage: 'plan', name: 'Test Planner', desc: 'Generates endpoint coverage strategy and awaits approval' },
  { id: 'generator', stage: 'generate', name: 'Test Generator', desc: 'Synthesizes targeted test payloads with schema validation' },
  { id: 'executor', stage: 'execute', name: 'Execution Engine', desc: 'Dispatches requests with rate limits and assertion checks' },
  { id: 'triage', stage: 'triage', name: 'Triage Agent', desc: 'Classifies true bugs vs false positives with OWASP Top 10' },
  { id: 'reporter', stage: 'report', name: 'Reporter Agent', desc: 'Generates HTML and PDF executive vulnerability reports' },
]

export function SessionDetail() {
  const { id } = useParams<{ id: string }>()
  const [session, setSession] = useState<Session | null>(null)
  const sessionStatus = session?.status
  const [planModalOpen, setPlanModalOpen] = useState(false)
  const [approving, setApproving] = useState(false)
  const [dismissedVersion, setDismissedVersion] = useState<number | null>(null)

  const fetchSession = useCallback(async () => {
    if (!id) return
    try {
      const res = await sessionsApi.get(id)
      setSession(res.data)
      if ((res.data.status === 'waiting_approval' || res.data.waiting_human)
        && res.data.waiting_reason !== 'generation_partial'
        && dismissedVersion !== res.data.plan_version) {
        setPlanModalOpen(true)
      }
    } catch {
      toast.error('Failed to load session')
    }
  }, [id, dismissedVersion])

  useEffect(() => {
    fetchSession()
  }, [fetchSession])

  // Session status is persisted separately from SSE events. Poll while active
  // so the header cannot remain stale during long generation/execution phases.
  useEffect(() => {
    if (!id || !sessionStatus || ['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(sessionStatus)) return
    const timer = window.setInterval(fetchSession, 2000)
    return () => window.clearInterval(timer)
  }, [id, sessionStatus, fetchSession])

  const { events, isConnected, isCompleted } = useSSE(id || null, {
    onEvent: (event) => {
      if (event.status === 'waiting_human') {
        fetchSession()
      }
      if (event.step === 'session_done' || event.step === 'session_error' || event.step === 'session_cancelled') {
        fetchSession()
        if (event.step === 'session_done') toast.success('Session completed successfully!')
        else if (event.step === 'session_error') toast.error(event.message || 'Session failed')
        else toast('Session cancelled')
      }
    },
  })

  const handleApprovePlan = async (approved: boolean) => {
    if (!id) return
    setApproving(true)
    try {
      await sessionsApi.approvePlan(id, approved, session?.plan_version ?? 0)
      toast.success(approved ? 'Plan approved! Resuming execution...' : 'Plan rejected.')
      setPlanModalOpen(false)
      setDismissedVersion(session?.plan_version ?? 0)
      fetchSession()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Approval failed')
    } finally {
      setApproving(false)
    }
  }

  const handleGenerationAction = async (action: 'retry' | 'continue' | 'abort') => {
    if (!id) return
    try {
      if (action === 'retry') await sessionsApi.retryStage(id, 'generate', true)
      else if (action === 'continue') await sessionsApi.continuePartial(id)
      else await sessionsApi.cancel(id)
      await fetchSession()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Unable to update the session')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'completed_with_errors':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />
      case 'running':
      case 'progress':
      case 'started':
        return <Lightning className="w-4 h-4 text-brand-600 animate-pulse" />
      case 'waiting_human':
      case 'waiting_approval':
        return <WarningCircle className="w-4 h-4 text-zinc-600" />
      case 'failed':
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-red-600" />
      default:
        return <Clock className="w-4 h-4 text-zinc-400" />
    }
  }

  const totalTokens = events.reduce((acc, ev) => acc + (ev.tokens || 0), 0)
  const totalLatency = events.reduce((acc, ev) => acc + (ev.latency_ms || 0), 0)
  const terminalStages = AGENT_STEPS.filter(({ stage }) => ['completed', 'completed_with_errors', 'skipped'].includes(session?.stages?.[stage]?.status || '')).length

  return (
    <div className="page-enter mx-auto max-w-[1500px] space-y-6">
      {/* Top Header Card */}
      <Card className="p-6 sm:p-7">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-12 bg-brand-600 flex items-center justify-center text-white">
                <Cpu className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-xl font-semibold tracking-tight text-[var(--app-text)] sm:text-2xl">
                  {session?.name || 'API Test Session'}
                </h1>
                <p className="mt-1 font-mono text-[11px] text-[var(--app-text-muted)]">
                  <span>SESSION</span> {id} <span className="mx-1 text-[#b4bbc7]">/</span> <span>TARGET</span> {session?.base_url || '—'}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            {/* Mode Badge */}
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold uppercase bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
              <ShieldCheck className="w-4 h-4 text-brand-600" />
              {session?.mode || 'local'} Mode
            </span>

            {/* Session Status */}
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold bg-brand-50 text-brand-900 border border-brand-200 dark:bg-brand-950/40 dark:text-brand-300 dark:border-brand-800">
              {getStatusIcon(session?.status || 'running')}
              <span className="capitalize">{session?.status?.replace('_', ' ') || 'Running'}</span>
            </span>

            {/* Link to Report if run created */}
            {session?.run_id && (
              <Link to={`/reports/${session.run_id}`}>
                <Button size="sm" variant="secondary">
                  <FileText className="w-4 h-4" />
                  <span>View Report</span>
                </Button>
              </Link>
            )}
          </div>
        </div>

        {/* Live Metrics Row */}
        <div className="mt-6 grid grid-cols-2 gap-4 border-t pt-5 sm:grid-cols-4">
          <div>
            <p className="text-xs text-[var(--app-text-muted)]">Stream status</p>
            <p className="text-sm font-semibold flex items-center gap-1.5 mt-0.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-[#25876b]' : 'bg-[#a8b0bd]'
                }`}
              />
              <span className="font-mono text-xs text-[var(--app-text)]">{isConnected ? 'CONNECTED · SSE' : isCompleted ? 'STREAM COMPLETE' : 'RECONNECTING'}</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--app-text-muted)]">Events streamed</p>
            <p className="mt-0.5 text-sm font-semibold text-[var(--app-text)]">
              {events.length}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--app-text-muted)]">Total tokens</p>
            <p className="mt-0.5 font-mono text-sm font-semibold text-[var(--app-text)]">
              {totalTokens.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--app-text-muted)]">Execution latency</p>
            <p className="mt-0.5 font-mono text-sm font-semibold text-[var(--app-text)]">
              {(totalLatency / 1000).toFixed(2)}s
            </p>
          </div>
        </div>
        <div className="mt-5 border-t pt-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[.12em] text-[var(--app-text-muted)]">Pipeline state</span>
            <span className="font-mono text-xs text-brand-600">{terminalStages} of {AGENT_STEPS.length} stages complete</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[var(--app-surface-muted)]">
            <div className="h-full rounded-full bg-brand-600 transition-[width] duration-500" style={{ width: `${(terminalStages / AGENT_STEPS.length) * 100}%` }} />
          </div>
        </div>
      </Card>

      {/* Session Failure Banner */}
      {session?.status === 'failed' && (
        <div className="p-4 rounded-16 bg-red-50 border-2 border-red-500 text-red-950 dark:bg-red-950/40 dark:text-red-200 flex items-start gap-3 animate-fade-in shadow-sm">
          <XCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-bold">Session Execution Failed</p>
            <p className="text-xs text-red-800 dark:text-red-300 font-mono">
              {session.error || events.find((e) => e.status === 'failed')?.message || 'An unexpected error occurred during pipeline execution.'}
            </p>
          </div>
        </div>
      )}

      {/* Human Approval Interrupt Banner */}
      {(session?.waiting_human || session?.status === 'waiting_approval') && (
        session?.waiting_reason === 'generation_partial' ? (
          <div className="p-4 rounded-16 bg-amber-50 border-2 border-amber-400 text-amber-950 dark:bg-amber-950/40 dark:text-amber-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <p className="text-sm font-bold">Generation completed below the coverage threshold</p>
              <p className="text-xs mt-1">Review the failed units, retry them, continue with generated cases, or abort.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => handleGenerationAction('retry')}>Retry failed units</Button>
              <Button size="sm" variant="secondary" onClick={() => handleGenerationAction('continue')}>Continue with partial</Button>
              <Button size="sm" variant="secondary" onClick={() => handleGenerationAction('abort')}>Abort</Button>
            </div>
          </div>
        ) : (
        <div className="p-4 rounded-16 bg-brand-50 border-2 border-brand-500 text-brand-900 dark:bg-brand-950/40 dark:text-brand-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 animate-fade-in shadow-sm">
          <div className="flex items-center gap-3">
            <WarningCircle className="w-6 h-6 text-brand-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold">Human Approval Required</p>
              <p className="text-xs text-zinc-600 dark:text-zinc-400">
                The PlannerAgent generated a coverage strategy. Please review the plan before tests are executed against the target.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setPlanModalOpen(true)}>
              Review & Approve Plan
            </Button>
          </div>
        </div>
        )
      )}

      <Card className="p-5 sm:p-6">
        <div className="mb-5 flex items-center justify-between gap-4"><div><h2 className="text-base font-semibold text-[var(--app-text)]">Execution workflow</h2><p className="mt-1 text-sm text-[var(--app-text-muted)]">Live state synchronized from the execution pipeline.</p></div><span className="font-mono text-xs text-[var(--app-text-muted)]">{terminalStages}/{AGENT_STEPS.length} complete</span></div>
        <ol className="grid gap-3 md:grid-cols-6" aria-label="Session execution workflow">
          {AGENT_STEPS.map((s, idx) => {
            const stage = session?.stages?.[s.stage]; const status = stage?.status || 'pending'; const progress = stage?.progress;
            const complete = status === 'completed' || status === 'skipped'; const failed = status === 'failed'; const waiting = status === 'waiting'; const active = status === 'running'; const partial = status === 'completed_with_errors';
            const tone = failed ? 'border-[#e5b5ba] bg-[#fbeef0]' : waiting || partial ? 'border-[#ead2ad] bg-[#fbf3e5]' : active ? 'border-brand-300 bg-brand-50' : complete ? 'border-[#b9dfd1] bg-[#eaf6f1]' : 'border-[var(--app-border)] bg-[var(--app-surface)]';
            const label = failed ? 'Failed' : waiting ? 'Awaiting approval' : partial ? 'Completed with errors' : active ? 'Running' : complete ? 'Completed' : 'Pending';
            return <li key={s.id} className={`relative rounded-lg border p-3 transition-colors ${tone}`}>
              {idx < AGENT_STEPS.length - 1 && <span className="absolute left-full top-7 hidden h-px w-3 bg-[var(--app-border)] md:block" />}
              <div className="flex items-start justify-between gap-2"><span className="font-mono text-[10px] text-[var(--app-text-muted)]">{String(idx + 1).padStart(2, '0')}</span>{complete ? <CheckCircle className="h-4 w-4 text-[#25876b]" /> : failed ? <XCircle className="h-4 w-4 text-[#c65c65]" /> : waiting ? <WarningCircle className="h-4 w-4 text-[#b98232]" /> : active ? <Lightning className="h-4 w-4 text-brand-600" /> : <Clock className="h-4 w-4 text-[#a7afbc]" />}</div>
              <p className="mt-4 text-xs font-semibold text-[var(--app-text)]">{s.name}</p><p className="mt-1 text-[11px] leading-4 text-[var(--app-text-muted)]">{label}</p>
              {progress?.total ? <div className="mt-3"><div className="h-1 overflow-hidden rounded-full bg-white/80"><div className="h-full bg-brand-600 transition-[width] duration-300" style={{ width: `${Math.min(100, Math.round(progress.done / progress.total * 100))}%` }} /></div><p className="mt-1 font-mono text-[10px] text-[var(--app-text-muted)]">{progress.done}/{progress.total}</p></div> : active ? <div className="mt-3 h-1 overflow-hidden rounded-full bg-brand-100"><span className="block h-full w-1/2 animate-pulse rounded-full bg-brand-500" /></div> : null}
              {waiting && s.stage === 'plan' && <Button size="sm" className="mt-3 w-full" onClick={() => setPlanModalOpen(true)}>Review plan</Button>}
            </li>
          })}
        </ol>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Card className="overflow-hidden p-0">
          <div className="flex items-center justify-between border-b px-5 py-4"><div><h2 className="text-base font-semibold text-[var(--app-text)]">Live activity</h2><p className="mt-0.5 text-xs text-[var(--app-text-muted)]">Agent activity and execution metadata.</p></div><span className="font-mono text-xs text-[var(--app-text-muted)]">{events.length} events</span></div>
          <div className="terminal-panel m-4 max-h-[420px] overflow-y-auto p-3">
            {events.length === 0 ? <div className="py-12 text-center text-sm text-[#aeb6c4]"><Clock className="mx-auto mb-2 h-6 w-6" />Connecting to the event stream…</div> : events.map((ev, i) => <div key={i} className="border-b border-white/10 px-2 py-3 last:border-0"><div className="flex flex-wrap items-center justify-between gap-2 font-mono text-[10px]"><span className="text-[#bbc4ff]">{ev.agent} / {ev.step}</span><span className="text-[#aeb6c4]">{new Date(ev.ts).toLocaleTimeString()}</span></div><p className="mt-1.5 text-sm leading-5 text-[#edf0f5]">{ev.message}</p><div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] text-[#aeb6c4]">{ev.tokens ? <span>{ev.tokens} tokens</span> : null}{ev.latency_ms ? <span>{ev.latency_ms}ms</span> : null}{ev.rag_used ? <span>RAG context</span> : null}{ev.repairs_used ? <span>{ev.repairs_used} repairs</span> : null}</div></div>)}
          </div>
        </Card>
        <Card className="p-5"><h2 className="text-base font-semibold text-[var(--app-text)]">Current session</h2><dl className="mt-5 space-y-4 text-sm"><div><dt className="text-xs text-[var(--app-text-muted)]">Mode</dt><dd className="mt-1 font-medium capitalize text-[var(--app-text)]">{session?.mode || 'local'}</dd></div><div><dt className="text-xs text-[var(--app-text-muted)]">Overall status</dt><dd className="mt-1 capitalize text-[var(--app-text)]">{session?.status?.replace('_', ' ') || 'Preparing'}</dd></div><div><dt className="text-xs text-[var(--app-text-muted)]">Current stage</dt><dd className="mt-1 text-[var(--app-text)]">{AGENT_STEPS.find(({ stage }) => session?.stages?.[stage]?.status === 'running')?.name || '—'}</dd></div></dl></Card>
      </div>

      {/* Plan Review Modal */}
      <Modal
        isOpen={planModalOpen}
        onClose={() => { setPlanModalOpen(false); setDismissedVersion(session?.plan_version ?? 0) }}
        title="Approve Test Plan Strategy"
        description="Review planned test categories and endpoint coverage before execution begins."
        size="lg"
      >
        <div className="space-y-4">
          <div className="p-4 rounded-12 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 max-h-72 overflow-auto space-y-2">
            {session?.plan?.endpoints && session.plan.endpoints.length > 0 ? (
              session.plan.endpoints.map((ep, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-8 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-brand-600 font-mono">{ep.method}</span>
                    <span className="font-mono text-zinc-800 dark:text-zinc-200">{ep.path}</span>
                  </div>
                  <div className="flex gap-1">
                    {ep.categories.map((c) => (
                      <span
                        key={c}
                        className="px-1.5 py-0.5 rounded-4 bg-zinc-100 dark:bg-zinc-800 text-[10px] capitalize text-zinc-600 dark:text-zinc-300"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-zinc-500">Plan details currently generating...</p>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => handleApprovePlan(false)}
              disabled={approving}
            >
              <ThumbsDown className="w-4 h-4" />
              <span>Reject plan</span>
            </Button>
            <Button
              onClick={() => handleApprovePlan(true)}
              loading={approving}
            >
              <ThumbsUp className="w-4 h-4" />
              <span>Approve & run</span>
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
