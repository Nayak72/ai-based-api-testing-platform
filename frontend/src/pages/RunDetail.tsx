import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useRun, useRunResults, useCancelRun, useRetryFailed, useAnalyzeRun, useGenerateReport } from '../hooks/useRuns'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge, StatusBadge, SeverityBadge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { Modal, ConfirmDialog } from '../components/ui/Modal'
import { usePolling } from '../hooks/usePolling'
import { PlayCircle, ArrowsClockwise, FileText, Brain } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function RunDetail() {
  const { runId } = useParams<{ runId: string }>()
  const [resultPage, setResultPage] = useState(1)
  const [resultPageSize] = useState(50)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [reportDialogOpen, setReportDialogOpen] = useState(false)
  const [reportFormat, setReportFormat] = useState<'html' | 'pdf' | 'both'>('html')
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false)
  const [confirmRetryOpen, setConfirmRetryOpen] = useState(false)

  const { data: runData, isLoading: runLoading, refetch: refetchRun } = useRun(runId!)
  const { data: resultsData, isLoading: resultsLoading, refetch: refetchResults } = useRunResults(runId!, resultPage, resultPageSize, statusFilter || undefined, categoryFilter || undefined)
  const cancelMutation = useCancelRun()
  const retryMutation = useRetryFailed()
  const analyzeMutation = useAnalyzeRun()
  const generateReportMutation = useGenerateReport()

  const { isPolling } = usePolling(runData?.data.status === 'running' || runData?.data.status === 'pending' ? runId! : null, {
    enabled: runData?.data.status === 'running' || runData?.data.status === 'pending',
    onStatusChange: (status) => {
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        refetchRun()
        refetchResults()
      }
    },
  })

  const run = runData?.data
  const results = resultsData?.data.results || []

  const handleCancel = async () => {
    try {
      await cancelMutation.mutateAsync(runId!)
      toast.success('Run cancelled')
      refetchRun()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to cancel')
    } finally {
      setConfirmCancelOpen(false)
    }
  }

  const handleRetry = async () => {
    try {
      await retryMutation.mutateAsync(runId!)
      toast.success('Retry started')
      refetchRun()
      refetchResults()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to retry')
    } finally {
      setConfirmRetryOpen(false)
    }
  }

  const handleAnalyze = async () => {
    try {
      await analyzeMutation.mutateAsync(runId!)
      toast.success('Analysis started')
      refetchResults()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Analysis failed')
    }
  }

  const handleGenerateReport = async () => {
    try {
      await generateReportMutation.mutateAsync({ runId: runId!, format: reportFormat })
      toast.success('Report generation started')
      setReportDialogOpen(false)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to generate report')
    }
  }

  if (runLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  if (!run) {
    return (
      <div className="text-center py-12">
        <PlayCircle className="h-12 w-12 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
        <p className="text-zinc-500 dark:text-zinc-400">Run not found</p>
      </div>
    )
  }

  const canCancel = run.status === 'running' || run.status === 'pending'
  const canRetry = run.status === 'completed' || run.status === 'failed'
  const canAnalyze = run.status === 'completed'
  const canReport = run.status === 'completed'

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/runs" className="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 mb-2 inline-block">
            ← Back to Runs
          </Link>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{run.name}</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">
            {run.config.categories.join(', ')} • Concurrency: {run.config.concurrency} • Timeout: {run.config.timeout_seconds}s
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <StatusBadge status={run.status} />
          {canCancel && (
            <Button variant="secondary" size="sm" onClick={() => setConfirmCancelOpen(true)}>
              Cancel
            </Button>
          )}
          {canRetry && (
            <Button variant="secondary" size="sm" onClick={() => setConfirmRetryOpen(true)}>
              <ArrowsClockwise className="h-4 w-4" />
              Retry Failed
            </Button>
          )}
          {canAnalyze && (
            <Button variant="secondary" size="sm" onClick={handleAnalyze} loading={analyzeMutation.isPending}>
              <Brain className="h-4 w-4" />
              Analyze
            </Button>
          )}
          {canReport && (
            <Button variant="secondary" size="sm" onClick={() => setReportDialogOpen(true)}>
              <FileText className="h-4 w-4" />
              Report
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="md">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Total</p>
          <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">{run.summary.total}</p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Passed</p>
          <p className="text-3xl font-bold text-green-600">{run.summary.passed}</p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Failed</p>
          <p className="text-3xl font-bold text-red-600">{run.summary.failed}</p>
        </Card>
        <Card padding="md">
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Duration</p>
          <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">{run.summary.duration_seconds?.toFixed(1)}s</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Test Results</CardTitle>
                  <CardDescription>{results.length} of {run.summary.total} results</CardDescription>
                </div>
                {isPolling && (
                  <div className="flex items-center gap-2 text-sm text-brand-600">
                    <PlayCircle className="h-4 w-4 animate-spin" />
                    Polling...
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {resultsLoading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
                </div>
              ) : results.length === 0 ? (
                <div className="text-center py-8 text-zinc-500 dark:text-zinc-400">No results yet</div>
              ) : (
                <>
                  <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <select
                      value={statusFilter}
                      onChange={(e) => { setStatusFilter(e.target.value); setResultPage(1); }}
                      className="input w-auto"
                    >
                      <option value="">All Status</option>
                      <option value="passed">Passed</option>
                      <option value="failed">Failed</option>
                      <option value="error">Error</option>
                      <option value="skipped">Skipped</option>
                    </select>
                    <select
                      value={categoryFilter}
                      onChange={(e) => { setCategoryFilter(e.target.value); setResultPage(1); }}
                      className="input w-auto"
                    >
                      <option value="">All Categories</option>
                      <option value="functional">Functional</option>
                      <option value="edge">Edge</option>
                      <option value="malformed">Malformed</option>
                      <option value="security">Security</option>
                    </select>
                  </div>
                  <Table
                    columns={[
                      { key: 'category', header: 'Category', width: '120px' },
                      { key: 'endpoint_id', header: 'Endpoint', sortable: true },
                      { key: 'status', header: 'Status', width: '100px' },
                      { key: 'duration_ms', header: 'Duration', width: '100px' },
                      { key: 'risk', header: 'Risk', width: '100px' },
                      { key: 'actions', header: '', width: '80px' },
                    ]}
                    data={results}
                    keyExtractor={(r) => r.id}
                    loading={resultsLoading}
                    emptyMessage="No results"
                  >
                    {({ row }) => (
                      <>
                        <td>
                          <Badge variant="default" className="capitalize">{row.category}</Badge>
                        </td>
                        <td className="font-mono text-sm text-zinc-900 dark:text-zinc-50 max-w-[250px] truncate">{row.endpoint_id}</td>
                        <td><StatusBadge status={row.status} /></td>
                        <td className="text-zinc-500 dark:text-zinc-400 text-sm">{row.response.duration_ms}ms</td>
                        <td>
                          {row.llm_analysis ? (
                            <SeverityBadge severity={row.llm_analysis.risk_level} />
                          ) : (
                            <Badge variant="gray" size="sm">—</Badge>
                          )}
                        </td>
                        <td>
                          <Link to={`/runs/${runId}/results/${row.id}`} className="p-2 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors">
                            <PlayCircle className="h-4 w-4" />
                          </Link>
                        </td>
                      </>
                    )}
                  </Table>
                  {resultsData && resultsData.data.total > resultPageSize && (
                    <Pagination
                      currentPage={resultPage}
                      totalPages={Math.ceil(resultsData.data.total / resultPageSize)}
                      onPageChange={setResultPage}
                      pageSize={resultPageSize}
                      totalItems={resultsData.data.total}
                    />
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Run Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Trigger</p>
                <p className="capitalize text-zinc-900 dark:text-zinc-50">{run.trigger}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Started</p>
                <p className="text-zinc-900 dark:text-zinc-50">{run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true }) : 'Not started'}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Completed</p>
                <p className="text-zinc-900 dark:text-zinc-50">{run.completed_at ? formatDistanceToNow(new Date(run.completed_at), { addSuffix: true }) : 'In progress'}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Config</p>
                <div className="text-sm text-zinc-600 dark:text-zinc-400 space-y-1">
                  <div>Concurrency: {run.config.concurrency}</div>
                  <div>Timeout: {run.config.timeout_seconds}s</div>
                  <div>Retries: {run.config.retry_failed}</div>
                  <div>Categories: {run.config.categories.join(', ')}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {run.config.base_url_override && (
            <Card>
              <CardHeader>
                <CardTitle>Overrides</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Base URL Override</p>
                  <p className="font-mono text-sm text-zinc-900 dark:text-zinc-50 break-all">{run.config.base_url_override}</p>
                </div>
                {run.config.auth_override && (
                  <div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Auth Override</p>
                    <p className="font-mono text-sm text-zinc-900 dark:text-zinc-50">{run.config.auth_override.token_env_var}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ConfirmDialog
        isOpen={confirmCancelOpen}
        onClose={() => setConfirmCancelOpen(false)}
        onConfirm={handleCancel}
        title="Cancel Test Run"
        message="Are you sure you want to cancel this running test run? In-flight requests will be allowed to complete."
        confirmText="Cancel Run"
        variant="danger"
        loading={cancelMutation.isPending}
      />

      <ConfirmDialog
        isOpen={confirmRetryOpen}
        onClose={() => setConfirmRetryOpen(false)}
        onConfirm={handleRetry}
        title="Retry Failed Tests"
        message="This will re-run only the failed and errored test cases from this run."
        confirmText="Retry"
        variant="primary"
        loading={retryMutation.isPending}
      />

      <Modal
        isOpen={reportDialogOpen}
        onClose={() => setReportDialogOpen(false)}
        title="Generate Report"
      >
        <div className="space-y-6">
          <p className="text-zinc-600 dark:text-zinc-400">Select report format:</p>
          <div className="grid grid-cols-3 gap-3">
            {(['html', 'pdf', 'both'] as const).map(fmt => (
              <label
                key={fmt}
                className={clsx(
                  'flex flex-col items-center gap-2 p-4 rounded-12 border-2 cursor-pointer transition-colors',
                  reportFormat === fmt ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                )}
              >
                <input
                  type="radio"
                  name="reportFormat"
                  value={fmt}
                  checked={reportFormat === fmt}
                  onChange={() => setReportFormat(fmt)}
                  className="sr-only"
                />
                <FileText className={clsx('h-8 w-8', reportFormat === fmt ? 'text-brand-600' : 'text-zinc-400')} />
                <span className="font-medium text-zinc-900 dark:text-zinc-50 capitalize">{fmt}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <Button variant="secondary" onClick={() => setReportDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleGenerateReport} loading={generateReportMutation.isPending}>
              <FileText className="h-4 w-4" />
              Generate
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}