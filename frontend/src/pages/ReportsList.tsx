import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useReports, useDownloadReport } from '../hooks/useRuns'
import { Card, CardHeader, CardContent } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Table, Pagination } from '../components/ui/Table'
import { FileText, Download, Eye, Clock } from '@phosphor-icons/react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function ReportsList() {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)

  const { data, isLoading } = useReports(page, pageSize)
  const downloadMutation = useDownloadReport()

  const handleDownload = async (reportId: string, format: 'html' | 'pdf') => {
    try {
      const response = await downloadMutation.mutateAsync({ reportId, format })
      const url = window.URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${reportId}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Downloaded ${format.toUpperCase()} report`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Download failed')
    }
  }

  const columns = [
    { key: 'run_id', header: 'Run ID', sortable: true },
    { key: 'format', header: 'Format', width: '120px' },
    { key: 'file_size_bytes', header: 'Size', width: '120px' },
    { key: 'generated_at', header: 'Generated', width: '180px', sortable: true },
    { key: 'actions', header: '', width: '160px' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Reports</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Generated test execution and compliance reports</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">All Reports</h2>
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
                data={data?.data.reports || []}
                keyExtractor={(report) => report.id}
                loading={isLoading}
                emptyMessage="No reports generated yet. Run a test and generate a report from the run details."
              >
                {({ row }) => (
                  <>
                    <td className="font-mono text-sm text-zinc-900 dark:text-zinc-50">
                      <Link to={`/reports/${row.run_id}`} className="text-brand-600 hover:underline">
                        {row.run_id}
                      </Link>
                    </td>
                    <td>
                      <Badge variant="info" size="sm" className="uppercase">
                        {row.format}
                      </Badge>
                    </td>
                    <td className="text-zinc-500 dark:text-zinc-400 text-sm">
                      {(row.file_size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td className="text-zinc-500 dark:text-zinc-400 text-sm">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-4 w-4 text-zinc-400" />
                        <span>{formatDistanceToNow(new Date(row.generated_at), { addSuffix: true })}</span>
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/reports/${row.run_id}`}
                          className="p-1.5 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
                          title="View Report"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                        {row.html_path && (
                          <button
                            onClick={() => handleDownload(row.id, 'html')}
                            className="p-1.5 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
                            title="Download HTML"
                          >
                            <FileText className="h-4 w-4" />
                          </button>
                        )}
                        {row.pdf_path && (
                          <button
                            onClick={() => handleDownload(row.id, 'pdf')}
                            className="p-1.5 rounded-8 text-zinc-500 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
                            title="Download PDF"
                          >
                            <Download className="h-4 w-4" />
                          </button>
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
    </div>
  )
}
