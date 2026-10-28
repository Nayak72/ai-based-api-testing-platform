import { useState } from 'react'
import { Card, Button, Input } from '../components/ui'
import { quickTestApi, QuickTestResponse } from '../api/endpoints'
import {
  PaperPlaneRight,
  ShieldCheck,
  Globe,
  Clock,
  CheckCircle,
  WarningCircle,
  XCircle,
  ArrowCounterClockwise,
} from '@phosphor-icons/react'
import toast from 'react-hot-toast'

export function QuickTest() {
  const [mode, setMode] = useState<'local' | 'online'>('local')
  const [method, setMethod] = useState<string>('GET')
  const [url, setUrl] = useState<string>('http://localhost:8001/products')
  const [authType, setAuthType] = useState<string>('none')
  const [authToken, setAuthToken] = useState<string>('')
  const [headersText, setHeadersText] = useState<string>('')
  const [bodyText, setBodyText] = useState<string>('{\n  \n}')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<QuickTestResponse | null>(null)

  const handleExecute = async () => {
    if (!url.trim()) {
      toast.error('URL is required')
      return
    }

    let parsedHeaders: Record<string, string> = {}
    if (headersText.trim()) {
      try {
        parsedHeaders = JSON.parse(headersText)
      } catch {
        toast.error('Headers must be valid JSON key-value pairs')
        return
      }
    }

    let parsedBody: any = null
    if (['POST', 'PUT', 'PATCH'].includes(method) && bodyText.trim()) {
      try {
        parsedBody = JSON.parse(bodyText)
      } catch {
        toast.error('Request body must be valid JSON')
        return
      }
    }

    setLoading(true)
    setResponse(null)
    try {
      const res = await quickTestApi.test({
        url,
        method,
        mode,
        headers: parsedHeaders,
        body: parsedBody,
        auth_type: authType === 'none' ? undefined : authType,
        auth_token: authToken || undefined,
      })
      setResponse(res.data)
      if (res.data.status_code >= 200 && res.data.status_code < 400) {
        toast.success(`Success: ${res.data.status_code}`)
      } else if (res.data.error) {
        toast.error(res.data.error)
      } else {
        toast(`Response: ${res.data.status_code}`, { icon: 'ℹ️' })
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Request failed'
      toast.error(msg)
      setResponse({
        status_code: err.response?.status || 0,
        headers: {},
        body: null,
        body_truncated: false,
        duration_ms: 0,
        error: msg,
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (code: number, error?: string | null) => {
    if (error || code === 0) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold bg-red-100 text-red-900 border border-red-300 dark:bg-red-950/60 dark:text-red-300 dark:border-red-800">
          <XCircle className="w-4 h-4 text-red-600" />
          <span>Blocked / Error</span>
        </span>
      )
    }
    if (code >= 200 && code < 300) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold bg-brand-50 text-brand-900 border border-brand-300 dark:bg-brand-950/60 dark:text-brand-300 dark:border-brand-800">
          <CheckCircle className="w-4 h-4 text-brand-600" />
          <span>{code} OK</span>
        </span>
      )
    }
    if (code >= 400 && code < 500) {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold bg-zinc-100 text-zinc-900 border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-200 dark:border-zinc-700">
          <WarningCircle className="w-4 h-4 text-zinc-600" />
          <span>{code} Client Error</span>
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-8 text-xs font-semibold bg-red-100 text-red-900 border border-red-300 dark:bg-red-950/60 dark:text-red-300 dark:border-red-800">
        <WarningCircle className="w-4 h-4 text-red-600" />
        <span>{code} Server Error</span>
      </span>
    )
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
            <PaperPlaneRight className="w-7 h-7 text-brand-600" />
            Quick Test
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            Execute single target requests through safety guards to inspect headers, latencies, and responses.
          </p>
        </div>

        {/* Mode Selector */}
        <div className="flex items-center p-1 bg-zinc-100 dark:bg-zinc-800 rounded-12 border border-zinc-200 dark:border-zinc-700 self-start">
          <button
            type="button"
            onClick={() => {
              setMode('local')
              if (url.includes('jsonplaceholder')) setUrl('http://localhost:8001/products')
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-8 text-xs font-medium transition-all ${
              mode === 'local'
                ? 'bg-white dark:bg-zinc-900 text-brand-600 shadow-sm'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            Local Mode (Dev/VulnShop)
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('online')
              if (url.includes('localhost')) setUrl('https://jsonplaceholder.typicode.com/posts/1')
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-8 text-xs font-medium transition-all ${
              mode === 'online'
                ? 'bg-white dark:bg-zinc-900 text-brand-600 shadow-sm'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900'
            }`}
          >
            <Globe className="w-4 h-4" />
            Online Mode (Public APIs)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Request Form */}
        <Card className="p-6 space-y-4">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Request Configuration</h2>

          {/* Method and URL */}
          <div className="flex gap-2">
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-28 rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm font-semibold text-brand-700 dark:text-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="PATCH">PATCH</option>
              <option value="DELETE">DELETE</option>
            </select>
            <div className="flex-1">
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://api.example.com/v1/resource"
                className="font-mono text-xs"
              />
            </div>
          </div>

          {/* Auth options */}
          <div className="space-y-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">Authentication</label>
            <div className="grid grid-cols-3 gap-2">
              {(['none', 'bearer', 'api_key'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setAuthType(type)}
                  className={`py-1.5 text-xs font-medium rounded-8 border transition-colors ${
                    authType === type
                      ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 text-zinc-600'
                  }`}
                >
                  {type === 'none' ? 'None' : type === 'bearer' ? 'Bearer Token' : 'X-API-Key'}
                </button>
              ))}
            </div>
            {authType !== 'none' && (
              <Input
                type="password"
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                placeholder={authType === 'bearer' ? 'ey...' : 'api-key-here'}
                className="font-mono text-xs mt-2"
              />
            )}
          </div>

          {/* Custom Headers */}
          <div className="space-y-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Headers (JSON format)
            </label>
            <textarea
              value={headersText}
              onChange={(e) => setHeadersText(e.target.value)}
              placeholder='{"Accept": "application/json"}'
              rows={3}
              className="w-full rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-2.5 font-mono text-xs text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>

          {/* Request Body */}
          {['POST', 'PUT', 'PATCH'].includes(method) && (
            <div className="space-y-1 pt-2 border-t border-zinc-100 dark:border-zinc-800">
              <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                JSON Body
              </label>
              <textarea
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                rows={5}
                className="w-full rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-2.5 font-mono text-xs text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              />
            </div>
          )}

          {/* Execute button */}
          <div className="pt-2">
            <Button
              onClick={handleExecute}
              loading={loading}
              className="w-full"
            >
              <PaperPlaneRight className="w-4 h-4" />
              <span>Send Request</span>
            </Button>
          </div>
        </Card>

        {/* Response Panel */}
        <Card className="p-6 space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Response</h2>
            {response && (
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-xs text-zinc-500 font-mono">
                  <Clock className="w-3.5 h-3.5" />
                  {response.duration_ms}ms
                </span>
                {getStatusBadge(response.status_code, response.error)}
              </div>
            )}
          </div>

          {!response && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-zinc-400">
              <ArrowCounterClockwise className="w-10 h-10 mb-2 opacity-40" />
              <p className="text-sm">No response yet. Configure and send a request to view output.</p>
            </div>
          )}

          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-zinc-500">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-500 border-t-transparent mb-3" />
              <p className="text-xs">Dispatching request through target safety guard...</p>
            </div>
          )}

          {response && !loading && (
            <div className="space-y-4 flex-1 flex flex-col">
              {response.error && (
                <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-12 text-xs text-red-700 dark:text-red-300 flex items-start gap-2">
                  <XCircle className="w-4 h-4 mt-0.5 text-red-600 flex-shrink-0" />
                  <span>{response.error}</span>
                </div>
              )}

              {response.body_truncated && (
                <div className="p-2 bg-zinc-100 dark:bg-zinc-800 rounded-8 text-xs text-zinc-600 dark:text-zinc-400">
                  Note: Response body was truncated at 50 KB.
                </div>
              )}

              <div className="flex-1 flex flex-col">
                <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">
                  Response Body
                </label>
                <div className="flex-1 overflow-auto max-h-96 rounded-12 border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 p-3 font-mono text-xs text-zinc-800 dark:text-zinc-200">
                  <pre className="whitespace-pre-wrap break-all">
                    {typeof response.body === 'object'
                      ? JSON.stringify(response.body, null, 2)
                      : String(response.body || 'No content')}
                  </pre>
                </div>
              </div>

              {Object.keys(response.headers || {}).length > 0 && (
                <div>
                  <details className="text-xs text-zinc-600 dark:text-zinc-400">
                    <summary className="cursor-pointer font-medium hover:text-zinc-900 dark:hover:text-zinc-200">
                      Response Headers ({Object.keys(response.headers).length})
                    </summary>
                    <div className="mt-2 max-h-40 overflow-auto rounded-8 bg-zinc-50 dark:bg-zinc-950 p-2 font-mono text-[11px] border border-zinc-200 dark:border-zinc-800">
                      {Object.entries(response.headers).map(([k, v]) => (
                        <div key={k} className="truncate">
                          <span className="font-semibold text-zinc-700 dark:text-zinc-300">{k}:</span> {v}
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
