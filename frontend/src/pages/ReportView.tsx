import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useReportByRun, useGenerateReport, useDownloadReport } from '../hooks/useRuns'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { FileText, Download, Clock, ArrowsClockwise, CaretLeft, Eye } from '@phosphor-icons/react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export function ReportView() {
  const { runId } = useParams<{ runId: string }>()
  const [reportFormat, setReportFormat] = useState<'html' | 'pdf' | 'both'>('html')
  const [reportGenerating, setReportGenerating] = useState(false)

  const { data: reportData, isLoading: reportLoading, refetch: refetchReport } = useReportByRun(runId!)
  const generateReportMutation = useGenerateReport()
  const downloadMutation = useDownloadReport()

  const report = reportData?.data

  const handleGenerateReport = async () => {
    setReportGenerating(true)
    try {
      await generateReportMutation.mutateAsync({ runId: runId!, format: reportFormat })
      toast.success('Report generation started')
      setTimeout(() => refetchReport(), 2000)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to generate report')
    } finally {
      setReportGenerating(false)
    }
  }

  const handleDownload = async (format: 'html' | 'pdf') => {
    if (!report) return
    try {
      const response = await downloadMutation.mutateAsync({ reportId: report.id, format })
      const url = window.URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${runId}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success(`Downloaded ${format.toUpperCase()} report`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Download failed')
    }
  }

  const handleViewHtml = async () => {
    if (!report) return
    try {
      const response = await downloadMutation.mutateAsync({ reportId: report.id, format: 'html' })
      const blob = new Blob([response.data], { type: 'text/html' })
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to open HTML report')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to={`/runs/${runId}`} className="p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
          <CaretLeft className="h-6 w-6" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Test Report</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">View and download test execution reports</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>Report Status</CardTitle>
              <CardDescription>Generate or download reports for this test run</CardDescription>
            </div>
            {!report && (
              <Button onClick={handleGenerateReport} loading={reportGenerating}>
                <FileText className="h-4 w-4" />
                Generate Report
              </Button>
            )}
            {report && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <select
                    value={reportFormat}
                    onChange={(e) => setReportFormat(e.target.value as 'html' | 'pdf' | 'both')}
                    className="input w-auto"
                  >
                    <option value="html">HTML</option>
                    <option value="pdf">PDF</option>
                    <option value="both">Both</option>
                  </select>
                  <Button variant="secondary" onClick={handleGenerateReport} loading={reportGenerating}>
                    <ArrowsClockwise className="h-4 w-4" />
                    Regenerate
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {reportLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-3 border-brand-500 border-t-transparent" />
            </div>
          ) : !report ? (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">No Report Generated</h3>
              <p className="text-zinc-500 dark:text-zinc-400 mb-6">Generate a report to view test results summary and detailed analysis</p>
              <Button onClick={handleGenerateReport} loading={reportGenerating}>
                <FileText className="h-4 w-4" />
                Generate Report
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card padding="md" variant="bordered">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-10 bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">Format</p>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50 capitalize">{report.format}</p>
                    </div>
                  </div>
                </Card>
                <Card padding="md" variant="bordered">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-10 bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                      <Clock className="h-5 w-5 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">Generated</p>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50">{formatDistanceToNow(new Date(report.generated_at), { addSuffix: true })}</p>
                    </div>
                  </div>
                </Card>
                <Card padding="md" variant="bordered">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-10 bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                      <Download className="h-5 w-5 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-sm text-zinc-500 dark:text-zinc-400">Size</p>
                      <p className="font-medium text-zinc-900 dark:text-zinc-50">{(report.file_size_bytes / 1024).toFixed(1)} KB</p>
                    </div>
                  </div>
                </Card>
              </div>

              <div className="flex flex-wrap gap-3">
                {report.html_path && (
                  <Button variant="secondary" onClick={() => handleDownload('html')}>
                    <Download className="h-4 w-4" />
                    Download HTML
                  </Button>
                )}
                {report.pdf_path && (
                  <Button variant="secondary" onClick={() => handleDownload('pdf')}>
                    <Download className="h-4 w-4" />
                    Download PDF
                  </Button>
                )}
                {report.html_path && (
                  <Button variant="ghost" onClick={handleViewHtml}>
                    <Eye className="h-4 w-4" />
                    View HTML
                  </Button>
                )}
              </div>

              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-6">
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  <strong>Disclaimer:</strong> AI-assisted testing, not a certified security audit
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {report && (
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Link to={`/runs/${runId}`} className="card-hover p-4 rounded-12 border border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-10 bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <ArrowsClockwise className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-zinc-900 dark:text-zinc-50">View Run Details</p>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">See test results and analysis</p>
                </div>
              </div>
            </Link>
            <Link to="/runs" className="card-hover p-4 rounded-12 border border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-10 bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium text-zinc-900 dark:text-zinc-50">All Test Runs</p>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">View run history</p>
                </div>
              </div>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  )
}