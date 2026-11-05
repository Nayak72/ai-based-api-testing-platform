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
  Database,
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
  const pipelinePercent = Math.round((terminalStages / AGENT_STEPS.length) * 100)

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
                <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                  {session?.name || 'API Security Session'}
                </h1>
                <p className="mt-1 font-mono text-[11px] text-slate-400">
                  <span className="text-slate-600">SESSION</span> {id} <span className="mx-1 text-slate-600">/</span> <span className="text-slate-600">TARGET</span> {session?.base_url || '—'}
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
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-[#1e3a5f]/70 pt-5 sm:grid-cols-4">
          <div>
            <p className="text-xs text-zinc-400">Stream Status</p>
            <p className="text-sm font-semibold flex items-center gap-1.5 mt-0.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-brand-600 animate-pulse' : 'bg-zinc-400'
                }`}
              />
              <span className="font-mono text-xs">{isConnected ? 'CONNECTED · SSE' : isCompleted ? 'STREAM COMPLETE' : 'RECONNECTING'}</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-400">Events Streamed</p>
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mt-0.5">
              {events.length}
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-400">Total Tokens</p>
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mt-0.5 font-mono">
              {totalTokens.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-400">Pipeline Latency</p>
            <p className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mt-0.5 font-mono">
              {(totalLatency / 1000).toFixed(2)}s
            </p>
          </div>
        </div>
        <div className="mt-5 border-t border-[#1e3a5f]/50 pt-4">
          <div className="mb-2 flex items-center justify-between gap-3">
            <span className="font-mono text-[10px] uppercase tracking-[.16em] text-slate-500">Pipeline completion</span>
            <span className="font-mono text-xs text-brand-300">{terminalStages}/{AGENT_STEPS.length} stages · {pipelinePercent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-[#020817] ring-1 ring-[#1e3a5f]/70">
            <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-400 transition-[width] duration-700" style={{ width: `${pipelinePercent}%` }} />
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

      {/* Main Grid: Stepper on Left, Event Stream on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Agent Stepper */}
        <div className="space-y-4">
          <h2 className="flex items-center gap-2 text-base font-bold text-slate-100">
            <Cpu className="h-5 w-5 text-brand-300" />
            <span>Agent Pipeline</span>
          </h2>

          <div className="space-y-2">
            {AGENT_STEPS.map((s, idx) => {
              const stage = session?.stages?.[s.stage]
              const stageStatus = stage?.status || 'pending'
              const hasFailed = stageStatus === 'failed'
              const isCompleted = stageStatus === 'completed' || stageStatus === 'skipped'
              const isWaiting = stageStatus === 'waiting'
              const isCurrent = stageStatus === 'running'
              const progress = stage?.progress
              const progressPct = progress?.total ? Math.min(100, Math.round(progress.done / progress.total * 100)) : 0

              return (
                <Card
                  key={s.id}
                  className={`stage-card p-4 transition-all ${
                    hasFailed
                      ? 'border-red-300 bg-red-50/40 dark:bg-red-950/30 shadow-sm'
                      : isCurrent
                      ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/30 shadow-sm'
                      : stageStatus === 'completed_with_errors'
                      ? 'border-amber-300 bg-amber-50/40 dark:bg-amber-950/30 shadow-sm'
                      : isCompleted
                      ? 'border-zinc-200 dark:border-zinc-800'
                      : 'border-zinc-100 dark:border-zinc-800/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      <span className={`flex h-6 w-6 items-center justify-center rounded-lg border font-mono text-[10px] ${isCompleted ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-300' : isCurrent ? 'border-cyan-300/40 bg-cyan-300/10 text-cyan-200' : hasFailed ? 'border-rose-400/30 bg-rose-400/10 text-rose-300' : 'border-[#1e3a5f] bg-[#07152a] text-slate-500'}`}>{String(idx + 1).padStart(2, '0')}</span>
                      {s.name}
                    </span>
                    {hasFailed ? (
                      <span className="text-red-600 text-xs font-bold flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" />
                        Failed
                      </span>
                    ) : isCompleted ? (
                      <span className="flex items-center gap-1 text-xs font-bold text-emerald-400">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Done
                      </span>
                    ) : isWaiting ? (
                      <span className="text-amber-600 text-xs font-bold flex items-center gap-1">
                        <WarningCircle className="w-3.5 h-3.5" />
                        Awaiting Approval
                      </span>
                    ) : stageStatus === 'completed_with_errors' ? (
                      <span className="text-amber-600 text-xs font-bold">{progress?.failed || 0} of {progress?.total || 0} failed</span>
                    ) : isCurrent ? (
                      <span className="text-brand-600 text-xs font-bold flex items-center gap-1">
                        <Lightning className="w-3.5 h-3.5 animate-pulse" />
                        Active
                      </span>
                    ) : (
                      <span className="text-zinc-400 text-xs">Pending</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">{s.desc}</p>
                  {isCurrent && progress?.total ? (
                    <div className="mt-2">
                      <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                        <div className="h-full bg-brand-600 transition-all" style={{ width: `${progressPct}%` }} />
                      </div>
                      <p className="mt-1 text-[10px] text-zinc-500">{progress.done}/{progress.total} complete · {progress.failed} failed</p>
                    </div>
                  ) : null}
                  {hasFailed && stage?.error ? <p className="mt-1 text-[11px] text-red-600">{stage.error}</p> : null}
                  {isWaiting && s.stage === 'plan' ? (
                    <Button size="sm" className="mt-2" onClick={() => setPlanModalOpen(true)}>Review plan</Button>
                  ) : null}
                </Card>
              )
            })}
          </div>
        </div>

        {/* Right Column: Live Event Stream */}
        <div className="space-y-4 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Lightning className="w-5 h-5 text-brand-600" />
              Live Agent Execution Trace
            </h2>
            <span className="text-xs text-zinc-400 font-mono">
              {events.length} events logged
            </span>
          </div>

          <div className="max-h-[calc(100vh-17rem)] space-y-3 overflow-y-auto pr-1">
            {events.length === 0 && (
              <Card className="p-8 text-center text-zinc-400">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Connecting to event stream...</p>
              </Card>
            )}

            {events.map((ev, i) => (
              <div
                key={i}
                className="glass-card animate-fade-in space-y-2 rounded-16 border border-[#1e3a5f]/70 p-4"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded-lg border border-brand-300/20 bg-brand-300/10 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wide text-brand-200">
                      {ev.agent}
                    </span>
                    <span className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                      {ev.step}
                    </span>
                  </div>

                  <span className="text-[11px] font-mono text-zinc-400">
                    {new Date(ev.ts).toLocaleTimeString()}
                  </span>
                </div>

                <p className="text-sm text-zinc-800 dark:text-zinc-200 leading-relaxed font-sans">
                  {ev.message}
                </p>

                {/* Metadata pills */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] font-mono text-zinc-500">
                  {ev.tokens ? (
                    <span className="px-2 py-0.5 rounded-6 bg-zinc-100 dark:bg-zinc-800">
                      {ev.tokens} tokens
                    </span>
                  ) : null}
                  {ev.latency_ms ? (
                    <span className="px-2 py-0.5 rounded-6 bg-zinc-100 dark:bg-zinc-800">
                      {ev.latency_ms}ms
                    </span>
                  ) : null}
                  {ev.rag_used && (
                    <span className="px-2 py-0.5 rounded-6 bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300 flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      RAG Context
                    </span>
                  )}
                  {ev.repairs_used ? (
                    <span className="px-2 py-0.5 rounded-6 bg-zinc-100 dark:bg-zinc-800">
                      {ev.repairs_used} json repairs
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
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
