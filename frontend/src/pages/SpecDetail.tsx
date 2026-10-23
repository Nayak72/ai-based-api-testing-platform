import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSpec, useSpecEndpoints, useParseSpec } from '../hooks/useSpecs'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge, StatusBadge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { Database, PlayCircle, ArrowsClockwise, Copy, Eye, Code } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function SpecDetail() {
  const { specId } = useParams<{ specId: string }>()
  const [endpointPage, setEndpointPage] = useState(1)
  const [endpointPageSize] = useState(20)
  const [showRawSpec, setShowRawSpec] = useState(false)

  const { data: specData, isLoading: specLoading, refetch: refetchSpec } = useSpec(specId!)
  const { data: endpointsData, isLoading: endpointsLoading } = useSpecEndpoints(specId!)
  const parseMutation = useParseSpec()

  const spec = specData?.data
  const endpoints = endpointsData?.data.endpoints || []

  const handleParse = async () => {
    try {
      await parseMutation.mutateAsync(specId!)
      toast.success('Parsing started')
      refetchSpec()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Parse failed')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  if (specLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  if (!spec) {
    return (
      <div className="text-center py-12">
        <Database className="h-12 w-12 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
        <p className="text-zinc-500 dark:text-zinc-400">Specification not found</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/specs" className="text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 mb-2 inline-block">
            ← Back to Specifications
          </Link>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">{spec.name}</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">
            {spec.source_type} • {spec.source_format} • {spec.endpoints_count} endpoints • {spec.spec_version || 'N/A'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={spec.status} />
          {spec.status === 'error' && (
            <Button variant="secondary" onClick={handleParse} loading={parseMutation.isPending} size="sm">
              <ArrowsClockwise className={clsx('h-4 w-4', parseMutation.isPending && 'animate-spin')} />
              Re-parse
            </Button>
          )}
          <Link to={`/specs/${specId}/test-cases`}>
            <Button>
              <PlayCircle className="h-4 w-4" />
              Generate Tests
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Endpoints</CardTitle>
              <CardDescription>{endpoints.length} endpoints found</CardDescription>
            </CardHeader>
            <CardContent>
              {endpointsLoading ? (
                <div className="flex justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
                </div>
              ) : endpoints.length === 0 ? (
                <div className="text-center py-8 text-zinc-500 dark:text-zinc-400">No endpoints found</div>
              ) : (
                <>
                  <Table
                    columns={[
                      { key: 'method', header: 'Method', width: '100px' },
                      { key: 'path', header: 'Path', sortable: true },
                      { key: 'summary', header: 'Summary' },
                      { key: 'actions', header: '', width: '100px' },
                    ]}
                    data={endpoints}
                    keyExtractor={(ep) => ep.endpoint_id}
                    loading={endpointsLoading}
                    emptyMessage="No endpoints"
                  >
                    {({ row }) => (
                      <>
                        <td>
                          <Badge variant={
                            row.method === 'GET' ? 'success' :
                            row.method === 'POST' ? 'info' :
                            row.method === 'PUT' || row.method === 'PATCH' ? 'warning' :
                            row.method === 'DELETE' ? 'error' : 'gray'
                          } size="sm">{row.method}</Badge>
                        </td>
                        <td className="font-mono text-sm text-zinc-900 dark:text-zinc-50">{row.path}</td>
                        <td className="text-zinc-600 dark:text-zinc-400 truncate max-w-[300px]">{row.summary || '—'}</td>
                        <td>
                          <Link to={`/specs/${specId}/test-cases?endpoint=${row.endpoint_id}`} className="p-2 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors" title="Test Cases">
                            <PlayCircle className="h-4 w-4" />
                          </Link>
                        </td>
                      </>
                    )}
                  </Table>
                  {endpointsData && endpointsData.data.total > endpointPageSize && (
                    <Pagination
                      currentPage={endpointPage}
                      totalPages={Math.ceil(endpointsData.data.total / endpointPageSize)}
                      onPageChange={setEndpointPage}
                      pageSize={endpointPageSize}
                      totalItems={endpointsData.data.total}
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
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Base URL</p>
                <p className="font-mono text-sm text-zinc-900 dark:text-zinc-50 break-all">{spec.base_url || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Status</p>
                <StatusBadge status={spec.status} />
              </div>
              {spec.parse_error && (
                <div className="p-3 rounded-8 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Parse Error</p>
                  <p className="text-sm text-red-600 dark:text-red-400">{spec.parse_error}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Created</p>
                <p className="text-sm text-zinc-900 dark:text-zinc-50">{formatDistanceToNow(new Date(spec.created_at), { addSuffix: true })}</p>
              </div>
              <div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Updated</p>
                <p className="text-sm text-zinc-900 dark:text-zinc-50">{formatDistanceToNow(new Date(spec.updated_at), { addSuffix: true })}</p>
              </div>
            </CardContent>
          </Card>

          {spec.auth_config && (
            <Card>
              <CardHeader>
                <CardTitle>Authentication Config</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="info" size="sm">{spec.auth_config.type}</Badge>
                </div>
                {spec.auth_config.token_env_var && (
                  <div>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-1">Token Env Var</p>
                    <div className="flex items-center gap-2">
                      <code className="font-mono text-sm text-zinc-900 dark:text-zinc-50 bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded-8">{spec.auth_config.token_env_var}</code>
                      <Button variant="ghost" size="sm" onClick={() => copyToClipboard(spec.auth_config.token_env_var!)}><Copy className="h-4 w-4" /></Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex items-center justify-between">
              <CardTitle>Raw Specification</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowRawSpec(!showRawSpec)}>
                {showRawSpec ? <Eye className="h-4 w-4" /> : <Code className="h-4 w-4" />}
                {showRawSpec ? 'Hide' : 'View'}
              </Button>
            </CardHeader>
            <CardContent>
              {showRawSpec ? (
                <div className="bg-zinc-950 rounded-8 p-4 max-h-96 overflow-auto font-mono text-xs text-zinc-300">
                  <pre>{spec.raw_content}</pre>
                </div>
              ) : (
                <p className="text-zinc-500 dark:text-zinc-400 text-center py-8">Click "View" to see the raw specification content</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}