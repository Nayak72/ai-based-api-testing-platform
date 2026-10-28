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
  { id: 'ingest', name: 'Ingest & Index', desc: 'Parses OpenAPI spec and indexes RAG vector chunks' },
  { id: 'planner', name: 'Test Planner', desc: 'Generates endpoint coverage strategy and awaits approval' },
  { id: 'generator', name: 'Test Generator', desc: 'Synthesizes targeted test payloads with schema validation' },
  { id: 'executor', name: 'Execution Engine', desc: 'Dispatches requests with rate limits and assertion checks' },
  { id: 'triage', name: 'Triage Agent', desc: 'Classifies true bugs vs false positives with OWASP Top 10' },
  { id: 'reporter', name: 'Reporter Agent', desc: 'Generates HTML and PDF executive vulnerability reports' },
]

export function SessionDetail() {
  const { id } = useParams<{ id: string }>()
  const [session, setSession] = useState<Session | null>(null)
  const sessionStatus = session?.status
  const [planModalOpen, setPlanModalOpen] = useState(false)
  const [approving, setApproving] = useState(false)

  const fetchSession = useCallback(async () => {
    if (!id) return
    try {
      const res = await sessionsApi.get(id)
      setSession(res.data)
      if (res.data.status === 'waiting_approval' || res.data.waiting_human) {
        setPlanModalOpen(true)
      }
    } catch {
      toast.error('Failed to load session')
    }
  }, [id])

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
      if (event.step === 'session_done') {
        fetchSession()
        toast.success('Session completed successfully!')
      }
    },
  })

  const handleApprovePlan = async (approved: boolean) => {
    if (!id) return
    setApproving(true)
    try {
      await sessionsApi.approvePlan(id, approved)
      toast.success(approved ? 'Plan approved! Resuming execution...' : 'Plan rejected.')
      setPlanModalOpen(false)
      fetchSession()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Approval failed')
    } finally {
      setApproving(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
      case 'completed_with_errors':
        return <CheckCircle className="w-4 h-4 text-brand-600" />
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

  // Active step inference
  const currentAgent = events[events.length - 1]?.agent || 'planner'
  const totalTokens = events.reduce((acc, ev) => acc + (ev.tokens || 0), 0)
  const totalLatency = events.reduce((acc, ev) => acc + (ev.latency_ms || 0), 0)

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header Card */}
      <Card className="p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="w-9 h-9 rounded-12 bg-brand-600 flex items-center justify-center text-white">
                <Cpu className="w-5 h-5" />
              </span>
              <div>
                <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
                  {session?.name || 'Autonomous Agent Session'}
                </h1>
                <p className="text-xs text-zinc-500 font-mono mt-0.5">
                  ID: {id} • Base URL: {session?.base_url || 'Default'}
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
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800">
          <div>
            <p className="text-xs text-zinc-400">Stream Status</p>
            <p className="text-sm font-semibold flex items-center gap-1.5 mt-0.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-brand-600 animate-pulse' : 'bg-zinc-400'
                }`}
              />
              {isConnected ? 'Connected (SSE)' : isCompleted ? 'Completed' : 'Offline'}
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
      )}

      {/* Main Grid: Stepper on Left, Event Stream on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Agent Stepper */}
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-brand-600" />
            Agent Pipeline
          </h2>

          <div className="space-y-2">
            {AGENT_STEPS.map((s, idx) => {
              const agentEvents = events.filter((e) => e.agent === s.id)
              const hasFailed = agentEvents.some((e) => e.status === 'failed')
              const isCompleted = agentEvents.some((e) => e.status === 'completed')
              const isWaiting = agentEvents.some((e) => e.status === 'waiting_human')
              const isStarted = agentEvents.some((e) => e.status === 'started' || e.status === 'progress')
              const isCurrent = currentAgent === s.id && session?.status === 'running'

              return (
                <Card
                  key={s.id}
                  className={`p-3.5 transition-all ${
                    hasFailed
                      ? 'border-red-300 bg-red-50/40 dark:bg-red-950/30 shadow-sm'
                      : isCurrent
                      ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/30 shadow-sm'
                      : isCompleted
                      ? 'border-zinc-200 dark:border-zinc-800'
                      : 'border-zinc-100 dark:border-zinc-800/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                      {idx + 1}. {s.name}
                    </span>
                    {hasFailed ? (
                      <span className="text-red-600 text-xs font-bold flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" />
                        Failed
                      </span>
                    ) : isCompleted ? (
                      <span className="text-brand-600 text-xs font-bold flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Done
                      </span>
                    ) : isWaiting ? (
                      <span className="text-amber-600 text-xs font-bold flex items-center gap-1">
                        <WarningCircle className="w-3.5 h-3.5" />
                        Awaiting Approval
                      </span>
                    ) : isCurrent || isStarted ? (
                      <span className="text-brand-600 text-xs font-bold flex items-center gap-1">
                        <Lightning className="w-3.5 h-3.5 animate-pulse" />
                        Active
                      </span>
                    ) : (
                      <span className="text-zinc-400 text-xs">Pending</span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-500 mt-1">{s.desc}</p>
                </Card>
              )
            })}
          </div>
        </div>

        {/* Right Column: Live Event Stream */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
              <Lightning className="w-5 h-5 text-brand-600" />
              Live Agent Execution Trace
            </h2>
            <span className="text-xs text-zinc-400 font-mono">
              {events.length} events logged
            </span>
          </div>

          <div className="space-y-3">
            {events.length === 0 && (
              <Card className="p-8 text-center text-zinc-400">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Connecting to event stream...</p>
              </Card>
            )}

            {events.map((ev, i) => (
              <div
                key={i}
                className="p-4 rounded-16 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm space-y-2 animate-fade-in"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-8 text-xs font-bold bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300 uppercase tracking-wide">
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
        onClose={() => setPlanModalOpen(false)}
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
              <span>Cancel Session</span>
            </Button>
            <Button
              onClick={() => handleApprovePlan(true)}
              loading={approving}
            >
              <ThumbsUp className="w-4 h-4" />
              <span>Approve & Execute</span>
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
