import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useTestCases, useGenerateTestCases, useDeleteTestCase } from '../hooks/useSpecs'
import { Card, CardHeader, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge, SeverityBadge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { Modal, ConfirmDialog } from '../components/ui/Modal'
import { Input } from '../components/ui/Input'
import { PlayCircle, Trash, Funnel, CheckCircle, XCircle, Database, Lightning, Shield } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

const CATEGORIES = [
  { value: 'functional', label: 'Functional', icon: CheckCircle },
  { value: 'edge', label: 'Edge Cases', icon: Lightning },
  { value: 'malformed', label: 'Malformed', icon: XCircle },
  { value: 'security', label: 'Security', icon: Shield },
]

export function TestCases() {
  const { specId } = useParams<{ specId: string }>()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get('category') || '')
  const [endpointFilter, setEndpointFilter] = useState(searchParams.get('endpoint') || '')
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false)
  const [selectedCategories, setSelectedCategories] = useState<string[]>(['functional', 'edge', 'malformed', 'security'])
  const [promptVersion, setPromptVersion] = useState('v1')
  const [customModel, setCustomModel] = useState(localStorage.getItem('ai_default_model') || '')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [testCaseToDelete, setTestCaseToDelete] = useState<string | null>(null)

  const { data, isLoading, refetch } = useTestCases(specId!, page, pageSize, endpointFilter || undefined, categoryFilter || undefined)
  const generateMutation = useGenerateTestCases()
  const deleteMutation = useDeleteTestCase()

  const handleGenerate = async () => {
    try {
      const aiProvider = localStorage.getItem('ai_primary_provider') || undefined
      const openRouterKey = localStorage.getItem('openrouter_api_key') || undefined
      const nimKey = localStorage.getItem('nim_api_key') || undefined
      const selectedModel = customModel.trim() || localStorage.getItem('ai_default_model') || undefined

      await generateMutation.mutateAsync({
        specId: specId!,
        data: {
          categories: selectedCategories,
          prompt_version: promptVersion,
          model: selectedModel,
          provider: aiProvider,
          api_key: aiProvider === 'nim' ? nimKey : openRouterKey,
        },
      })
      toast.success('Test generation started')
      setGenerateDialogOpen(false)
      refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Generation failed')
    }
  }

  const handleDelete = async () => {
    if (!testCaseToDelete) return
    try {
      await deleteMutation.mutateAsync({ specId: specId!, testCaseId: testCaseToDelete })
      toast.success('Test case deleted')
      refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to delete')
    } finally {
      setDeleteDialogOpen(false)
      setTestCaseToDelete(null)
    }
  }

  const categoryIcons: Record<string, any> = {
    functional: CheckCircle,
    edge: Lightning,
    malformed: XCircle,
    security: Shield,
  }

  const columns = [
    { key: 'category', header: 'Category', width: '140px' },
    { key: 'subcategory', header: 'Subcategory', width: '160px' },
    { key: 'title', header: 'Title', sortable: true },
    { key: 'endpoint_id', header: 'Endpoint' },
    { key: 'metadata.severity', header: 'Severity', width: '100px' },
    { key: 'actions', header: '', width: '80px' },
  ]

  const handleCategoryChange = (cat: string) => {
    setSelectedCategories(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Test Cases</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Generated test cases for this specification</p>
        </div>
        <Button onClick={() => setGenerateDialogOpen(true)}>
          <PlayCircle className="h-4 w-4" />
          Generate Tests
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
                  placeholder="Filter by endpoint..."
                  value={endpointFilter}
                  onChange={(e) => { setEndpointFilter(e.target.value); setPage(1); }}
                  className="input pl-10 w-64"
                />
              </div>
              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                className="input w-auto"
              >
                <option value="">All Categories</option>
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
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
                data={data?.data.test_cases || []}
                keyExtractor={(tc) => tc.id}
                loading={isLoading}
                emptyMessage="No test cases found"
              >
                {({ row }) => {
                  const Icon = categoryIcons[row.category] || Database
                  return (
                    <>
                      <td>
                        <Badge variant="default" className="flex items-center gap-1">
                          <Icon className="h-3 w-3" />
                          {row.category}
                        </Badge>
                      </td>
                      <td className="text-zinc-600 dark:text-zinc-400 text-sm">{row.subcategory}</td>
                      <td className="font-medium text-zinc-900 dark:text-zinc-50 max-w-[300px] truncate">{row.title}</td>
                      <td className="font-mono text-sm text-zinc-500 dark:text-zinc-400">{row.endpoint_id}</td>
                      <td><SeverityBadge severity={row.metadata.severity} /></td>
                      <td>
                        <button
                          onClick={(e) => { e.stopPropagation(); setTestCaseToDelete(row.id); setDeleteDialogOpen(true); }}
                          className="p-2 rounded-8 text-zinc-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete"
                        >
                          <Trash className="h-4 w-4" />
                        </button>
                      </td>
                    </>
                  )
                }}
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
        isOpen={generateDialogOpen}
        onClose={() => setGenerateDialogOpen(false)}
        title="Generate Test Cases"
        size="md"
      >
        <div className="space-y-6">
          <p className="text-zinc-600 dark:text-zinc-400">Select categories to generate test cases for:</p>
          <div className="grid grid-cols-2 gap-3">
            {CATEGORIES.map(cat => {
              const Icon = cat.icon
              const isSelected = selectedCategories.includes(cat.value)
              return (
                <label
                  key={cat.value}
                  className={clsx(
                    'flex items-center gap-3 p-4 rounded-12 border-2 transition-colors cursor-pointer',
                    isSelected ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600'
                  )}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleCategoryChange(cat.value)}
                    className="w-4 h-4 text-brand-600 rounded-6 border-zinc-300 focus:ring-brand-500"
                  />
                  <Icon className={clsx('h-5 w-5', isSelected ? 'text-brand-600' : 'text-zinc-400')} />
                  <span className="font-medium text-zinc-900 dark:text-zinc-50">{cat.label}</span>
                </label>
              )
            })}
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">AI Model</label>
            <Input
              value={customModel}
              onChange={(e) => setCustomModel(e.target.value)}
              placeholder="e.g. meta-llama/llama-3.3-70b-instruct:free (or leave as configured)"
              helperText="Specify the AI model to use for generating these tests (e.g. any free model on OpenRouter)"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Prompt Version</label>
            <Input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} placeholder="v1" />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-zinc-200 dark:border-zinc-800">
            <Button variant="secondary" onClick={() => setGenerateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleGenerate} loading={generateMutation.isPending}>
              <PlayCircle className="h-4 w-4" />
              Generate
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={deleteDialogOpen}
        onClose={() => { setDeleteDialogOpen(false); setTestCaseToDelete(null); }}
        onConfirm={handleDelete}
        title="Delete Test Case"
        message="Are you sure you want to delete this test case? This action cannot be undone."
        confirmText="Delete"
        variant="danger"
        loading={deleteMutation.isPending}
      />
    </div>
  )
}