import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSpecs, useDeleteSpec, useParseSpec } from '../hooks/useSpecs'
import { Card, CardHeader, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { StatusBadge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { ConfirmDialog } from '../components/ui/Modal'
import { FileText, PlayCircle, Trash, ArrowsClockwise, MagnifyingGlass, Plus } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function SpecsList() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [specToDelete, setSpecToDelete] = useState<string | null>(null)

  const { data, isLoading, error, refetch } = useSpecs(page, pageSize, statusFilter || undefined)
  const deleteMutation = useDeleteSpec()
  const parseMutation = useParseSpec()

  const handleDelete = async () => {
    if (!specToDelete) return
    try {
      await deleteMutation.mutateAsync(specToDelete)
      toast.success('Specification deleted')
      refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    } finally {
      setDeleteDialogOpen(false)
      setSpecToDelete(null)
    }
  }

  const columns = [
    { key: 'name', header: 'Name', sortable: true },
    { key: 'endpoints_count', header: 'Endpoints', sortable: true },
    { key: 'status', header: 'Status' },
    { key: 'created_at', header: 'Created', sortable: true },
    { key: 'actions', header: '' },
  ]

  const specs = (data?.data.specs || []).filter(spec =>
    search ? spec.name.toLowerCase().includes(search.toLowerCase()) : true
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Specifications</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Manage your API specifications</p>
        </div>
        <Link to="/specs/upload">
          <Button>
            <Plus className="h-4 w-4" />
            Upload Spec
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 h-5 w-5" />
                <input
                  type="text"
                  placeholder="Search specs..."
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
                <option value="parsing">Parsing</option>
                <option value="ready">Ready</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
            </div>
          ) : error ? (
            <div className="text-center py-8 text-red-600">Failed to load specifications</div>
          ) : (
            <>
              <Table
                columns={columns}
                data={specs}
                keyExtractor={(spec) => spec.id}
                loading={isLoading}
                emptyMessage="No specifications found"
                onRowClick={(spec) => navigate(`/specs/${spec.id}`)}
              >
                {({ row }) => (
                  <>
                    <td className="font-medium text-zinc-900 dark:text-zinc-50">{row.name}</td>
                    <td className="text-zinc-600 dark:text-zinc-400">{row.endpoints_count}</td>
                    <td><StatusBadge status={row.status} /></td>
                    <td className="text-zinc-500 dark:text-zinc-400 text-sm">{formatDistanceToNow(new Date(row.created_at), { addSuffix: true })}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Link to={`/specs/${row.id}`} className="p-2 rounded-8 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors" title="View">
                          <FileText className="h-4 w-4" />
                        </Link>
                        <Link to={`/specs/${row.id}/test-cases`} className="p-2 rounded-8 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors" title="Test Cases">
                          <PlayCircle className="h-4 w-4" />
                        </Link>
                        {row.status === 'error' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); parseMutation.mutate(row.id); }}
                            disabled={parseMutation.isPending}
                            className="p-2 rounded-8 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50"
                            title="Re-parse"
                          >
                            <ArrowsClockwise className={clsx('h-4 w-4', parseMutation.isPending && 'animate-spin')} />
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); setSpecToDelete(row.id); setDeleteDialogOpen(true); }}
                          className="p-2 rounded-8 text-zinc-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete"
                        >
                          <Trash className="h-4 w-4" />
                        </button>
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

      <ConfirmDialog
        isOpen={deleteDialogOpen}
        onClose={() => { setDeleteDialogOpen(false); setSpecToDelete(null); }}
        onConfirm={handleDelete}
        title="Delete Specification"
        message="Are you sure you want to delete this specification? This will also delete all associated test cases and runs. This action cannot be undone."
        confirmText="Delete"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}