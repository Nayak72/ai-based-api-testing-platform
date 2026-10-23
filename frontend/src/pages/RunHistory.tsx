import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useRuns, useCreateRun } from '../hooks/useRuns'
import { specsApi } from '../api/endpoints'
import { Card, CardHeader, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge, StatusBadge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { Modal } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { PlayCircle, ClockCounterClockwise, Funnel, Plus, FileText } from '@phosphor-icons/react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function RunHistory() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [specFilter, setSpecFilter] = useState(searchParams.get('spec_id') || '')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', spec_id: '', concurrency: 10, timeout_seconds: 30, retry_failed: 1, categories: ['functional', 'edge', 'malformed', 'security'] })
  const [specs, setSpecs] = useState<Array<{id: string, name: string}>>([])

  const { data, isLoading, refetch } = useRuns(page, pageSize, specFilter || undefined, statusFilter || undefined)
  const createMutation = useCreateRun()

  useEffect(() => {
    loadSpecs()
  }, [])

  const loadSpecs = async () => {
    try {
      const response = await specsApi.list({ page: 1, page_size: 100 })
      setSpecs(response.data.specs.map(s => ({ id: s.id, name: s.name })))
    } catch {
      // ignore
    }
  }

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync(createForm)
      toast.success('Test run created')
      setCreateDialogOpen(false)
      setCreateForm({ name: '', spec_id: '', concurrency: 10, timeout_seconds: 30, retry_failed: 1, categories: ['functional', 'edge', 'malformed', 'security'] })
      refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create run')
    }
  }

  const filteredRuns = (data?.data.runs || []).filter(run => {
    if (search && !run.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const columns = [
    { key: 'name', header: 'Name', sortable: true },
    { key: 'spec_id', header: 'Spec' },
    { key: 'status', header: 'Status', width: '120px' },
    { key: 'summary', header: 'Results', width: '200px' },
    { key: 'duration', header: 'Duration', width: '100px' },
    { key: 'created_at', header: 'Created', width: '140px', sortable: true },
    { key: 'actions', header: '', width: '100px' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Test Runs</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">History of test executions and results</p>
        </div>
        <Button onClick={() => { loadSpecs(); setCreateDialogOpen(true); }}>
          <Plus className="h-4 w-4" />
          New Run
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="relative">
                <Funnel className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 h-5 w-5" />
                <input
                  type="text"
                  placeholder="Filter by name..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="input pl-10 w-64"
                />
              </div>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="input w-auto"
              >
                <option value="">All Status</option>
                <option value="pending">Pending</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <select
                value={specFilter}
                onChange={(e) => { setSpecFilter(e.target.value); setPage(1); }}
                className="input w-auto"
              >
                <option value="">All Specs</option>
                {specs.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
            </div>
          ) : (
            <>
              <Table
                columns={columns}
                data={filteredRuns}
                keyExtractor={(run) => run.id}
                loading={isLoading}
                emptyMessage="No test runs found"
                onRowClick={(run) => navigate(`/runs/${run.id}`)}
              >
                {({ row }) => (
                  <>
                    <td className="font-medium text-zinc-900 dark:text-zinc-50 max-w-[200px] truncate">{row.name}</td>
                    <td className="text-zinc-600 dark:text-zinc-400 text-sm">{specs.find(s => s.id === row.spec_id)?.name || row.spec_id}</td>
                    <td><StatusBadge status={row.status} /></td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Badge variant="success" size="sm">{row.summary.passed} passed</Badge>
                        {row.summary.failed > 0 && <Badge variant="error" size="sm">{row.summary.failed} failed</Badge>}
                        {row.summary.errors > 0 && <Badge variant="warning" size="sm">{row.summary.errors} errors</Badge>}
                        {row.summary.skipped > 0 && <Badge variant="gray" size="sm">{row.summary.skipped} skipped</Badge>}
                      </div>
                    </td>
                    <td className="text-zinc-500 dark:text-zinc-400 text-sm">{row.summary.duration_seconds?.toFixed(1)}s</td>
                    <td className="text-zinc-500 dark:text-zinc-400 text-sm">{formatDistanceToNow(new Date(row.created_at), { addSuffix: true })}</td>
                    <td>
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <Link to={`/runs/${row.id}`} className="p-1.5 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors" title="View Run">
                          <ClockCounterClockwise className="h-4 w-4" />
                        </Link>
                        {row.status === 'completed' && (
                          <Link to={`/reports/${row.id}`} className="p-1.5 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors" title="View Report">
                            <FileText className="h-4 w-4" />
                          </Link>
                        )}
                      </div>
                    </td>
                  </>
                )}
              </Table>
              {data && data.data.total > pageSize && (
                <Pagination
                  currentPage={page}
                  totalPages={Math.ceil(data.data.total / pageSize)}
                  onPageChange={setPage}
                  pageSize={pageSize}
                  totalItems={data.data.total}
                  showPageSize
                />
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Modal
        isOpen={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        title="Create Test Run"
        size="lg"
      >
        <div className="space-y-6">
          <Input
            label="Run Name"
            value={createForm.name}
            onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
            placeholder="Nightly regression - 2024-01-15"
            required
          />
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Specification *</label>
            <select
              value={createForm.spec_id}
              onChange={(e) => setCreateForm({...createForm, spec_id: e.target.value})}
              className="input"
              required
            >
              <option value="">Select a specification</option>
              {specs.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Input
              label="Concurrency"
              type="number"
              value={createForm.concurrency}
              onChange={(e) => setCreateForm({...createForm, concurrency: parseInt(e.target.value)})}
              min={1}
              max={100}
            />
            <Input
              label="Timeout (seconds)"
              type="number"
              value={createForm.timeout_seconds}
              onChange={(e) => setCreateForm({...createForm, timeout_seconds: parseFloat(e.target.value)})}
              min={1}
              max={300}
            />
            <Input
              label="Retry Failed"
              type="number"
              value={createForm.retry_failed}
              onChange={(e) => setCreateForm({...createForm, retry_failed: parseInt(e.target.value)})}
              min={0}
              max={5}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Categories</label>
            <div className="flex flex-wrap gap-2">
              {['functional', 'edge', 'malformed', 'security'].map(cat => (
                <label key={cat} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={createForm.categories.includes(cat)}
                    onChange={(e) => setCreateForm({
                      ...createForm,
                      categories: e.target.checked
                        ? [...createForm.categories, cat]
                        : createForm.categories.filter(c => c !== cat)
                    })}
                    className="w-4 h-4 text-brand-600 rounded-4 border-zinc-300 focus:ring-brand-500"
                  />
                  <span className="text-sm text-zinc-700 dark:text-zinc-300 capitalize">{cat}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <Button variant="secondary" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={createMutation.isPending}>
              <PlayCircle className="h-4 w-4" />
              Create Run
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}