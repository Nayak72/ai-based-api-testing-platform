import { Link, useParams } from 'react-router-dom'
import { useRunResult } from '../hooks/useRuns'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge, SeverityBadge, StatusBadge } from '../components/ui/Badge'

export function RunResultDetail() {
  const { runId = '', resultId = '' } = useParams<{ runId: string; resultId: string }>()
  const { data, isLoading, error } = useRunResult(runId, resultId)
  const result = data?.data

  if (isLoading) return <div className="flex justify-center py-12"><div className="h-8 w-8 animate-spin rounded-full border-3 border-brand-500 border-t-transparent" /></div>
  if (error || !result) return <div className="space-y-4"><Link to={`/runs/${runId}`} className="text-sm text-brand-600 hover:underline">← Back to run</Link><p className="text-zinc-600 dark:text-zinc-300">Result not found or could not be loaded.</p></div>

  const analysis = result.llm_analysis
  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div>
        <Link to={`/runs/${runId}`} className="text-sm text-zinc-500 hover:text-brand-600">← Back to run results</Link>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <h2 className="break-all text-2xl font-bold text-zinc-950 dark:text-white">{result.endpoint_id}</h2>
          <StatusBadge status={result.status} />
          <Badge variant="default" className="capitalize">{result.category}</Badge>
          {analysis && <SeverityBadge severity={analysis.risk_level} />}
        </div>
        <p className="mt-2 text-sm text-zinc-500">HTTP {result.response.status_code} · {result.response.duration_ms} ms · Attempt {result.attempt}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Request</CardTitle><CardDescription>Sent to the target API</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            <p className="font-mono text-sm break-all">{result.request_sent.method} {result.request_sent.url}</p>
            <pre className="max-h-96 overflow-auto rounded-xl bg-zinc-950 p-4 text-xs text-zinc-100">{JSON.stringify({ headers: result.request_sent.headers, body: result.request_sent.body }, null, 2)}</pre>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Response</CardTitle><CardDescription>Received from the target API</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {result.error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 dark:bg-rose-950/30 dark:text-rose-300">{result.error}</p>}
            <pre className="max-h-96 overflow-auto rounded-xl bg-zinc-950 p-4 text-xs text-zinc-100">{JSON.stringify({ headers: result.response.headers, body: result.response.body, body_truncated: result.response.body_truncated }, null, 2)}</pre>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Assertions</CardTitle><CardDescription>{result.assertions.length} checks</CardDescription></CardHeader>
        <CardContent className="space-y-2">
          {result.assertions.length === 0 ? <p className="text-sm text-zinc-500">No assertions were recorded.</p> : result.assertions.map((item, index) => (
            <div key={`${index}-${item.assertion?.type ?? 'assertion'}`} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
              <div className="flex flex-wrap items-center justify-between gap-3"><p className="font-medium text-[var(--app-text)]">{item.name || item.assertion?.type || 'Assertion'}</p><StatusBadge status={item.result ? 'passed' : 'failed'} /></div>
              <div className="mt-2 grid gap-2 text-xs text-[var(--app-text-muted)] sm:grid-cols-2"><p><span className="font-medium">Path:</span> <code>{item.path || item.assertion?.path || '—'}</code></p><p><span className="font-medium">Operator:</span> {item.operator || item.assertion?.operator || '—'}</p><p><span className="font-medium">Expected:</span> <code>{JSON.stringify(item.expected ?? item.assertion?.value)}</code></p><p><span className="font-medium">Actual:</span> <code>{JSON.stringify(item.actual)}</code></p></div>
              {item.message && <p className="mt-2 text-sm text-[#c65c65]">{item.message}</p>}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Analysis</CardTitle><CardDescription>AI assessment saved for this test result</CardDescription></CardHeader>
        <CardContent>
          {!analysis ? <p className="text-sm text-zinc-500">No analysis has been saved for this result yet. Run Analyze from the run page after execution completes.</p> : (
            <div className="space-y-4">
              <p className="text-zinc-800 dark:text-zinc-200">{analysis.summary}</p>
              {analysis.findings?.length > 0 && <div><h3 className="mb-2 font-semibold">Findings</h3><ul className="list-disc space-y-2 pl-5">{analysis.findings.map((finding: any, index: number) => <li key={index} className="text-sm"><span className="font-medium">{finding.type}: </span>{finding.description}{finding.evidence && <p className="mt-1 text-zinc-500">Evidence: {finding.evidence}</p>}</li>)}</ul></div>}
              {analysis.recommendations?.length > 0 && <div><h3 className="mb-2 font-semibold">Recommendations</h3><ul className="list-disc space-y-1 pl-5 text-sm">{analysis.recommendations.map((item: string, index: number) => <li key={index}>{item}</li>)}</ul></div>}
              <p className="text-xs text-zinc-500">False-positive likelihood: {Math.round((analysis.false_positive_likelihood ?? 0) * 100)}%</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
