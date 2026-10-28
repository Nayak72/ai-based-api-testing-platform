import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Database, FileArrowUp, FileText, PlayCircle, Plus, RocketLaunch, Clock } from '@phosphor-icons/react'
import { reportsApi, runsApi, specsApi } from '../api/endpoints'
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, EmptyState, ErrorState, Skeleton, StatusBadge } from '../components/ui'

function MetricCard({ label, value, detail, icon: Icon, href, loading }: {
  label: string
  value: number | string
  detail: string
  icon: typeof Database
  href: string
  loading?: boolean
}) {
  return (
    <Link to={href} className="group rounded-16 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950">
      <Card variant="hover" className="h-full p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">{label}</p>
            {loading ? <Skeleton className="mt-3 h-9 w-14" /> : <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">{value}</p>}
            <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{detail}</p>
          </div>
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-12 bg-brand-50 text-brand-700 transition-transform group-hover:-translate-y-0.5 dark:bg-brand-400/10 dark:text-brand-300">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
        </div>
      </Card>
    </Link>
  )
}

export function Dashboard() {
  const specs = useQuery({ queryKey: ['specs', 1, 5], queryFn: () => specsApi.list({ page: 1, page_size: 5 }) })
  const runs = useQuery({ queryKey: ['runs', 1, 5], queryFn: () => runsApi.list({ page: 1, page_size: 5 }) })
  const reports = useQuery({ queryKey: ['reports', 1, 1], queryFn: () => reportsApi.list({ page: 1, page_size: 1 }) })
  const activeRuns = useQuery({ queryKey: ['runs', 'running', 1, 1], queryFn: () => runsApi.list({ status: 'running', page: 1, page_size: 1 }) })

  const retryAll = () => {
    void specs.refetch()
    void runs.refetch()
    void reports.refetch()
    void activeRuns.refetch()
  }
  const hasLoadError = specs.isError || runs.isError || reports.isError || activeRuns.isError
  const recentRuns = runs.data?.data.runs ?? []
  const recentSpecs = specs.data?.data.specs ?? []

  return (
    <div className="mx-auto max-w-7xl space-y-7 page-enter">
      <section className="page-header">
        <div>
          <p className="page-kicker">Security testing workbench</p>
          <h2 className="text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">Good to see you</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">Start a guided audit, monitor current executions, and keep your API specifications ready for testing.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/specs/upload"><Button variant="secondary"><FileArrowUp className="h-4 w-4" /> Upload spec</Button></Link>
          <Link to="/sessions/new"><Button><Plus className="h-4 w-4" /> New session</Button></Link>
        </div>
      </section>

      {hasLoadError && <ErrorState title="Some dashboard data could not be loaded" description="Counts may be unavailable until the connection is restored. Existing values are not presented as zero." onRetry={retryAll} />}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Workspace totals">
        <MetricCard label="Specifications" value={specs.data?.data.total ?? '—'} detail="All uploaded API contracts" icon={Database} href="/specs" loading={specs.isLoading} />
        <MetricCard label="Test runs" value={runs.data?.data.total ?? '—'} detail="All scheduled and completed runs" icon={PlayCircle} href="/runs" loading={runs.isLoading} />
        <MetricCard label="Reports" value={reports.data?.data.total ?? '—'} detail="Generated report records" icon={FileText} href="/reports" loading={reports.isLoading} />
        <MetricCard label="Active runs" value={activeRuns.data?.data.total ?? '—'} detail="Runs currently executing" icon={Clock} href="/runs?status=running" loading={activeRuns.isLoading} />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4"><div><CardTitle>Recent test runs</CardTitle><CardDescription>Latest execution activity from your workspace.</CardDescription></div><Link to="/runs" className="text-sm font-semibold text-brand-700 hover:text-brand-800 dark:text-brand-300">View all</Link></CardHeader>
          <CardContent>
            {runs.isLoading ? <div className="space-y-3">{[1, 2, 3].map((item) => <Skeleton key={item} className="h-16 w-full" />)}</div> : runs.isError ? <ErrorState title="Runs are unavailable" description="Retry to load recent execution activity." onRetry={() => void runs.refetch()} /> : recentRuns.length === 0 ? <EmptyState title="No test runs yet" description="Create a session to generate a plan and start your first API audit." action={<Link to="/sessions/new"><Button size="sm"><RocketLaunch className="h-4 w-4" /> Create session</Button></Link>} icon={<PlayCircle className="mb-3 h-8 w-8 text-slate-400" />} /> : <div className="divide-y divide-slate-100 dark:divide-slate-800">{recentRuns.map((run) => <Link key={run.id} to={`/runs/${run.id}`} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:bg-slate-50/70 dark:hover:bg-slate-800/40"><div className="min-w-0"><p className="truncate font-medium text-slate-900 dark:text-slate-100">{run.name}</p><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}</p></div><div className="flex shrink-0 items-center gap-3"><span className="hidden text-sm text-slate-500 sm:inline">{run.summary.passed}/{run.summary.total}</span><StatusBadge status={run.status} /></div></Link>)}</div>}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4"><div><CardTitle>Recent specifications</CardTitle><CardDescription>Contracts available to use in a new session.</CardDescription></div><Link to="/specs" className="text-sm font-semibold text-brand-700 hover:text-brand-800 dark:text-brand-300">View all</Link></CardHeader>
          <CardContent>
            {specs.isLoading ? <div className="space-y-3">{[1, 2, 3].map((item) => <Skeleton key={item} className="h-16 w-full" />)}</div> : specs.isError ? <ErrorState title="Specifications are unavailable" description="Retry to load your recent API contracts." onRetry={() => void specs.refetch()} /> : recentSpecs.length === 0 ? <EmptyState title="No specifications uploaded" description="Upload an OpenAPI document, then use it to configure a test session." action={<Link to="/specs/upload"><Button size="sm"><FileArrowUp className="h-4 w-4" /> Upload specification</Button></Link>} icon={<Database className="mb-3 h-8 w-8 text-slate-400" />} /> : <div className="divide-y divide-slate-100 dark:divide-slate-800">{recentSpecs.map((spec) => <Link key={spec.id} to={`/specs/${spec.id}`} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:bg-slate-50/70 dark:hover:bg-slate-800/40"><div className="min-w-0"><p className="truncate font-medium text-slate-900 dark:text-slate-100">{spec.name}</p><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{spec.endpoints_count} endpoints · {formatDistanceToNow(new Date(spec.created_at), { addSuffix: true })}</p></div><StatusBadge status={spec.status} /></Link>)}</div>}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
