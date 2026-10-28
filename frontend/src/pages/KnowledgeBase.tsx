import { useState, useEffect } from 'react'
import { Card, Button, Input } from '../components/ui'
import { kbApi, KBStatus } from '../api/endpoints'
import {
  Books,
  MagnifyingGlass,
  ArrowClockwise,
  ShieldCheck,
  Sparkle,
  CheckCircle,
} from '@phosphor-icons/react'
import toast from 'react-hot-toast'

const OWASP_TOP10 = [
  { id: 'api1_bola', code: 'API1:2023', name: 'Broken Object Level Authorization (BOLA)', desc: 'Attackers manipulate IDs to access unauthorized objects.' },
  { id: 'api2_broken_auth', code: 'API2:2023', name: 'Broken Authentication', desc: 'Flawed token validation, weak hashing, or missing expiration.' },
  { id: 'api3_bopla', code: 'API3:2023', name: 'Broken Object Property Level Authorization', desc: 'Excessive data exposure and mass assignment vulnerabilities.' },
  { id: 'api4_resource_consumption', code: 'API4:2023', name: 'Unrestricted Resource Consumption', desc: 'Lack of rate limits, unbounded page sizes, high payload sizes.' },
  { id: 'api5_bfla', code: 'API5:2023', name: 'Broken Function Level Authorization (BFLA)', desc: 'Regular users accessing administrative or privileged actions.' },
  { id: 'api6_business_flow', code: 'API6:2023', name: 'Unrestricted Access to Sensitive Business Flows', desc: 'Automated purchasing, brute forcing, or workflow gaming.' },
  { id: 'api7_ssrf', code: 'API7:2023', name: 'Server Side Request Forgery (SSRF)', desc: 'APIs fetching untrusted remote resources without URI validation.' },
  { id: 'api8_misconfiguration', code: 'API8:2023', name: 'Security Misconfiguration', desc: 'Debug endpoints exposed, unhandled stack traces, open CORS.' },
  { id: 'api9_inventory', code: 'API9:2023', name: 'Improper Inventory Management', desc: 'Outdated API versions (v1 alongside v2), unpatched shadow APIs.' },
  { id: 'api10_unsafe_consumption', code: 'API10:2023', name: 'Unsafe Consumption of APIs', desc: 'Blindly trusting 3rd-party webhook and upstream responses.' },
]

export function KnowledgeBase() {
  const [status, setStatus] = useState<KBStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [reindexing, setReindexing] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])

  const fetchStatus = async () => {
    try {
      const res = await kbApi.status()
      setStatus(res.data)
    } catch {
      toast.error('Failed to load KB status')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
  }, [])

  const handleReindex = async () => {
    setReindexing(true)
    try {
      await kbApi.reindex()
      toast.success('Knowledge Base re-indexing started in background')
      setTimeout(() => {
        fetchStatus()
        setReindexing(false)
      }, 2000)
    } catch {
      toast.error('Failed to trigger re-index')
      setReindexing(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchQuery.trim()) return

    setSearching(true)
    try {
      const res = await kbApi.search(searchQuery.trim(), undefined, 6)
      setSearchResults(res.data.results || [])
      if (!res.data.results || res.data.results.length === 0) {
        toast('No matching vector chunks found', { icon: 'ℹ️' })
      }
    } catch {
      toast.error('Search failed')
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
            <Books className="w-7 h-7 text-brand-600" />
            Security Knowledge Base
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            ChromaDB vector store containing OWASP Top 10 (2023), RFC HTTP patterns, and spec chunks.
          </p>
        </div>

        <Button
          onClick={handleReindex}
          loading={reindexing}
          variant="secondary"
          size="sm"
          className="self-start"
        >
          <ArrowClockwise className="w-4 h-4" />
          <span>Re-index KB</span>
        </Button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Total Indexed Chunks</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1">
            {loading ? '-' : status?.total || 0}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">OWASP Top 10 Chunks</p>
          <p className="text-2xl font-bold text-brand-600 mt-1">
            {loading ? '-' : status?.owasp_count || 10}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">HTTP Standards Chunks</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1">
            {loading ? '-' : status?.http_kb_count || 3}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-zinc-500 dark:text-zinc-400">Spec Endpoints & Schemas</p>
          <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mt-1">
            {loading ? '-' : status?.spec_chunks_count || 0}
          </p>
        </Card>
      </div>

      {/* Vector Search Box */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2 mb-3">
          <Sparkle className="w-5 h-5 text-brand-600" />
          Semantic Vector Search
        </h2>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="flex-1">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="e.g. Broken object level authorization on order ID or status 403 handling"
              className="text-sm"
            />
          </div>
          <Button type="submit" loading={searching} className="px-6">
            <MagnifyingGlass className="w-4 h-4" />
            <span>Search</span>
          </Button>
        </form>

        {searchResults.length > 0 && (
          <div className="mt-6 space-y-3">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
              Search Results ({searchResults.length})
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {searchResults.map((res, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-12 border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-brand-600">
                      {res.metadata?.category || res.metadata?.kind || 'KB Document'}
                    </span>
                    {res.score !== undefined && (
                      <span className="text-[11px] font-mono text-zinc-400">
                        dist: {Number(res.score).toFixed(3)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-zinc-700 dark:text-zinc-300 line-clamp-3 font-mono">
                    {res.text || res.document}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* OWASP Top 10 Reference */}
      <div className="space-y-3">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-brand-600" />
          OWASP API Security Top 10 (2023) Reference Documents
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {OWASP_TOP10.map((item) => (
            <Card key={item.id} className="p-4 hover:border-brand-500/50 transition-colors">
              <div className="flex items-start justify-between gap-2">
                <span className="px-2 py-0.5 rounded-8 text-xs font-bold font-mono bg-brand-50 text-brand-700 border border-brand-200 dark:bg-brand-950/40 dark:text-brand-300 dark:border-brand-800">
                  {item.code}
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] text-zinc-500 font-medium">
                  <CheckCircle className="w-3.5 h-3.5 text-brand-600" />
                  Embedded in KB
                </span>
              </div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mt-2">
                {item.name}
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                {item.desc}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
