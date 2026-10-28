import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Input } from '../components/ui'
import {
  specsApi,
  catalogApi,
  providersApi,
  sessionsApi,
  Spec,
  CatalogItem,
  ProviderProfile,
} from '../api/endpoints'
import {
  ShieldCheck,
  Globe,
  Database,
  RocketLaunch,
  Cpu,
  ArrowRight,
  ArrowLeft,
  Storefront,
} from '@phosphor-icons/react'
import toast from 'react-hot-toast'

export function NewSession() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)

  // Step 1: Mode
  const [mode, setMode] = useState<'local' | 'online'>('local')

  // Step 2: Spec source
  const [sourceType, setSourceType] = useState<'catalog' | 'vulnshop' | 'existing' | 'url'>('vulnshop')
  const [specs, setSpecs] = useState<Spec[]>([])
  const [selectedSpecId, setSelectedSpecId] = useState<string>('')
  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([])
  const [selectedCatalogId, setSelectedCatalogId] = useState<string>('jsonplaceholder')
  const [urlInput, setUrlInput] = useState<string>('')
  const [importingUrl, setImportingUrl] = useState(false)

  // Step 3: Target & Auth
  const [baseUrl, setBaseUrl] = useState<string>('http://localhost:8001')
  const [authType, setAuthType] = useState<'none' | 'bearer' | 'api_key'>('none')
  const [authToken, setAuthToken] = useState<string>('')
  const [secondaryAuthType, setSecondaryAuthType] = useState<'none' | 'bearer' | 'api_key'>('none')
  const [secondaryAuthToken, setSecondaryAuthToken] = useState<string>('')
  const [ownedAttestation, setOwnedAttestation] = useState(false)

  // Step 4: AI & Routing
  const [providers, setProviders] = useState<ProviderProfile[]>([])
  const [selectedProviderId, setSelectedProviderId] = useState<string>('')
  const [agentic, setAgentic] = useState(true)

  // Step 5: Scope & Intensity
  const [categories, setCategories] = useState<string[]>(['functional', 'edge', 'malformed', 'security'])
  const [intensity, setIntensity] = useState<'quick' | 'normal' | 'deep'>('normal')

  // Launch state
  const [launching, setLaunching] = useState(false)
  const [sessionName, setSessionName] = useState('Security & Functional Audit')

  useEffect(() => {
    // Load existing specs
    specsApi.list({ page_size: 100 }).then((res) => {
      setSpecs(res.data.specs || [])
    }).catch(() => {})

    // Load catalog
    catalogApi.list().then((res) => {
      setCatalogItems(res.data.catalog || [])
    }).catch(() => {})

    // Load providers
    providersApi.list().then((res) => {
      const list: ProviderProfile[] = Array.isArray(res.data)
        ? res.data
        : (res.data as any)?.providers ?? []
      setProviders(list)
      if (list.length > 0) {
        setSelectedProviderId(list[0].id)
      }
    }).catch(() => {})
  }, [])

  const handleSourceChange = (type: 'catalog' | 'vulnshop' | 'existing' | 'url') => {
    setSourceType(type)
    if (type === 'vulnshop') {
      setMode('local')
      setBaseUrl('http://localhost:8001')
      setSessionName('VulnShop Security Assessment')
    } else if (type === 'catalog') {
      setMode('online')
      const item = catalogItems.find((c) => c.id === selectedCatalogId)
      if (item) {
        setBaseUrl(item.base_url)
        setSessionName(`${item.name} Assessment`)
      }
    }
  }

  const handleUrlImport = async () => {
    if (!urlInput.trim()) {
      toast.error('Enter a valid URL')
      return
    }
    setImportingUrl(true)
    try {
      const res = await specsApi.importFromUrl({ url: urlInput.trim(), mode })
      toast.success('Spec imported successfully')
      setSelectedSpecId(res.data.id)
      setSourceType('existing')
      // Refresh specs
      const refreshed = await specsApi.list({ page_size: 100 })
      setSpecs(refreshed.data.specs || [])
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Import failed')
    } finally {
      setImportingUrl(false)
    }
  }

  const toggleCategory = (cat: string) => {
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    )
  }

  const handleStartSession = async () => {
    setLaunching(true)
    try {
      let finalSpecId = selectedSpecId

      // If VulnShop, find or import VulnShop bundled spec
      if (sourceType === 'vulnshop') {
        const vsSpec = specs.find(
          (s) => s.name.toLowerCase().includes('vulnshop') && s.status === 'ready' && (s.endpoints_count || 0) > 0
        )
        if (vsSpec) {
          finalSpecId = vsSpec.id
        } else {
          // Import VulnShop bundled catalog entry
          const res = await catalogApi.import('vulnshop', { mode: 'local', name: 'VulnShop (Demo Target)' })
          finalSpecId = res.data.spec_id
        }
      } else if (sourceType === 'catalog') {
        // Import catalog spec
        const res = await catalogApi.import(selectedCatalogId, { mode })
        finalSpecId = res.data.spec_id
      }

      if (!finalSpecId) {
        // Fallback to first available spec
        if (specs.length > 0) {
          finalSpecId = specs[0].id
        } else {
          toast.error('Please select or import a specification first')
          setLaunching(false)
          return
        }
      }

      const res = await sessionsApi.create({
        spec_id: finalSpecId,
        name: sessionName || 'Test Session',
        mode,
        base_url: baseUrl || undefined,
        auth_type: authType === 'none' ? undefined : authType,
        auth_token: authToken || undefined,
        provider_profile_id: selectedProviderId || undefined,
        categories,
        intensity,
        agentic,
      })

      toast.success('Test Session initiated!')
      navigate(`/sessions/${res.data.session_id || res.data.id}`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start session')
      setLaunching(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
          <RocketLaunch className="w-7 h-7 text-brand-600" />
          New Test Session
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Configure an AI-powered security and functional audit session.
        </p>
      </div>

      {/* Stepper Progress */}
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-4">
        {[
          { num: 1, label: 'Mode' },
          { num: 2, label: 'Target & Spec' },
          { num: 3, label: 'Auth & Safety' },
          { num: 4, label: 'AI Strategy' },
          { num: 5, label: 'Review & Launch' },
        ].map((s) => (
          <div key={s.num} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                step === s.num
                  ? 'bg-brand-600 text-white'
                  : step > s.num
                  ? 'bg-brand-100 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300'
                  : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'
              }`}
            >
              {step > s.num ? '✓' : s.num}
            </div>
            <span
              className={`text-xs font-medium hidden sm:inline ${
                step === s.num ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-400'
              }`}
            >
              {s.label}
            </span>
          </div>
        ))}
      </div>

      {/* STEP 1: MODE */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Select Execution Mode</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              onClick={() => {
                setMode('local')
                setBaseUrl('http://localhost:8001')
              }}
              className={`p-6 rounded-16 border-2 cursor-pointer transition-all ${
                mode === 'local'
                  ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/20 shadow-sm'
                  : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="w-10 h-10 rounded-12 bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center text-brand-600">
                  <ShieldCheck className="w-6 h-6" />
                </span>
                {mode === 'local' && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-8 bg-brand-600 text-white">
                    Selected
                  </span>
                )}
              </div>
              <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Local Mode</h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1.5 leading-relaxed">
                For testing local APIs, Docker targets, and VulnShop. Allows localhost (127.0.0.1, 8001, etc.) and RFC1918 private IPs. Public Internet targets are blocked.
              </p>
            </div>

            <div
              onClick={() => {
                setMode('online')
                setBaseUrl('https://jsonplaceholder.typicode.com')
              }}
              className={`p-6 rounded-16 border-2 cursor-pointer transition-all ${
                mode === 'online'
                  ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/20 shadow-sm'
                  : 'border-zinc-200 dark:border-zinc-800 hover:border-zinc-300'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="w-10 h-10 rounded-12 bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-700 dark:text-zinc-300">
                  <Globe className="w-6 h-6" />
                </span>
                {mode === 'online' && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-8 bg-brand-600 text-white">
                    Selected
                  </span>
                )}
              </div>
              <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Online Mode</h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1.5 leading-relaxed">
                For testing public staging and production APIs safely. Automatically blocks internal/private IPs and AWS metadata (169.254.169.254). Strict 2 RPS rate limit.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* STEP 2: SPEC SOURCE */}
      {step === 2 && (
        <Card className="p-6 space-y-5">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">API Target & Specification</h2>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { id: 'vulnshop', label: 'VulnShop (Demo)', icon: Storefront },
              { id: 'catalog', label: 'Public Catalog', icon: Globe },
              { id: 'existing', label: 'Existing Spec', icon: Database },
              { id: 'url', label: 'Import from URL', icon: ArrowRight },
            ].map((s) => {
              const Icon = s.icon
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => handleSourceChange(s.id as any)}
                  className={`p-3 rounded-12 border text-xs font-semibold flex flex-col items-center gap-1.5 transition-all ${
                    sourceType === s.id
                      ? 'border-brand-600 bg-brand-50/60 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300 shadow-sm'
                      : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 hover:bg-zinc-50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{s.label}</span>
                </button>
              )
            })}
          </div>

          {sourceType === 'vulnshop' && (
            <div className="p-4 rounded-12 bg-brand-50/50 dark:bg-brand-950/30 border border-brand-200 dark:border-brand-800 text-xs text-brand-900 dark:text-brand-300 space-y-2">
              <p className="font-semibold flex items-center gap-1.5">
                <Storefront className="w-4 h-4 text-brand-600" />
                VulnShop Demo Environment Pre-configured
              </p>
              <p className="text-zinc-600 dark:text-zinc-400">
                Tests against the vulnerable store at <code className="font-mono font-bold">http://localhost:8001</code>.
                Contains BOLA, BFLA, Mass Assignment, Debug Endpoint Exposure, and Unbounded Listing flaws.
              </p>
            </div>
          )}

          {sourceType === 'catalog' && (
            <div className="space-y-3">
              <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                Select Pre-configured Public API
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {catalogItems.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      setSelectedCatalogId(item.id)
                      setBaseUrl(item.base_url)
                      setSessionName(`${item.name} Assessment`)
                    }}
                    className={`p-3 rounded-12 border cursor-pointer transition-all ${
                      selectedCatalogId === item.id
                        ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/20'
                        : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50'
                    }`}
                  >
                    <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">{item.name}</p>
                    <p className="text-[11px] text-zinc-500 font-mono mt-0.5 truncate">{item.base_url}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {sourceType === 'existing' && (
            <div className="space-y-2">
              <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                Choose Uploaded Spec
              </label>
              <select
                value={selectedSpecId}
                onChange={(e) => setSelectedSpecId(e.target.value)}
                className="w-full rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
              >
                {specs.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.endpoints_count} endpoints)
                  </option>
                ))}
              </select>
            </div>
          )}

          {sourceType === 'url' && (
            <div className="space-y-2">
              <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
                OpenAPI Spec URL (JSON or YAML)
              </label>
              <div className="flex gap-2">
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://petstore.swagger.io/v2/swagger.json"
                  className="font-mono text-xs"
                />
                <Button onClick={handleUrlImport} loading={importingUrl}>
                  Import
                </Button>
              </div>
            </div>
          )}

          <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <Input
              label="Target Base URL Override"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:8001"
              className="font-mono text-xs"
            />
          </div>
        </Card>
      )}

      {/* STEP 3: AUTH & SAFETY */}
      {step === 3 && (
        <Card className="p-6 space-y-5">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Authentication & Target Safety</h2>

          {/* Primary Auth */}
          <div className="space-y-2">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Primary Identity (e.g. Regular User)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['none', 'bearer', 'api_key'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setAuthType(t)}
                  className={`py-1.5 text-xs font-medium rounded-8 border transition-colors ${
                    authType === t
                      ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  {t === 'none' ? 'No Auth' : t === 'bearer' ? 'Bearer Token' : 'X-API-Key'}
                </button>
              ))}
            </div>
            {authType !== 'none' && (
              <Input
                type="password"
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                placeholder="Paste token (encrypted at rest; never shown in UI)"
                className="font-mono text-xs mt-2"
              />
            )}
          </div>

          {/* Secondary Auth for BOLA/BFLA */}
          <div className="space-y-2 pt-3 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Secondary Identity (For BOLA & BFLA Cross-Account Verification)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['none', 'bearer', 'api_key'] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setSecondaryAuthType(t)}
                  className={`py-1.5 text-xs font-medium rounded-8 border transition-colors ${
                    secondaryAuthType === t
                      ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  {t === 'none' ? 'None' : t === 'bearer' ? 'Bearer Token' : 'X-API-Key'}
                </button>
              ))}
            </div>
            {secondaryAuthType !== 'none' && (
              <Input
                type="password"
                value={secondaryAuthToken}
                onChange={(e) => setSecondaryAuthToken(e.target.value)}
                placeholder="Second user token for unauthorized object access tests"
                className="font-mono text-xs mt-2"
              />
            )}
          </div>

          {/* Owned Host Attestation for Online mode */}
          {mode === 'online' && (
            <div className="p-4 rounded-12 border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/60 space-y-2">
              <label className="flex items-start gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={ownedAttestation}
                  onChange={(e) => setOwnedAttestation(e.target.checked)}
                  className="mt-0.5 rounded text-brand-600 focus:ring-brand-500"
                />
                <div className="text-xs">
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                    Owned Host Attestation
                  </span>
                  <p className="text-zinc-500 dark:text-zinc-400 mt-0.5 leading-relaxed">
                    I attest that I own or have written authorization to perform security testing against this host. (Security categories will be disabled in Online mode without this).
                  </p>
                </div>
              </label>
            </div>
          )}
        </Card>
      )}

      {/* STEP 4: AI STRATEGY & SCOPE */}
      {step === 4 && (
        <Card className="p-6 space-y-5">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">AI Engine & Test Scope</h2>

          {/* Provider Profile */}
          <div className="space-y-2">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              AI Provider Profile
            </label>
            <select
              value={selectedProviderId}
              onChange={(e) => setSelectedProviderId(e.target.value)}
              className="w-full rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            >
              <option value="">Default Cloud (From Server .env)</option>
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.preset ?? p.provider_type} — {p.model ?? p.default_model})
                </option>
              ))}
            </select>
          </div>

          {/* Agentic mode toggle */}
          <div className="p-4 rounded-12 border border-brand-200 dark:border-brand-800 bg-brand-50/40 dark:bg-brand-950/20 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold text-brand-900 dark:text-brand-300 flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-brand-600" />
                Autonomous Agentic Pipeline
              </p>
              <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                Generates a test strategy plan, interrupts for human approval, triages bug findings, and streams live agent events via SSE.
              </p>
            </div>
            <input
              type="checkbox"
              checked={agentic}
              onChange={(e) => setAgentic(e.target.checked)}
              className="mt-1 rounded text-brand-600 focus:ring-brand-500 w-4 h-4"
            />
          </div>

          {/* Test Categories */}
          <div className="space-y-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Test Categories
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {[
                { id: 'functional', label: 'Functional Happy-Path' },
                { id: 'edge', label: 'Edge & Boundaries' },
                { id: 'malformed', label: 'Malformed Payloads' },
                { id: 'security', label: 'OWASP Security' },
              ].map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => toggleCategory(c.id)}
                  className={`p-2.5 rounded-8 text-xs font-semibold border transition-colors ${
                    categories.includes(c.id)
                      ? 'border-brand-600 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 text-zinc-400 hover:bg-zinc-50'
                  }`}
                >
                  {categories.includes(c.id) ? '✓ ' : '+ '}
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Intensity */}
          <div className="space-y-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Test Intensity
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['quick', 'normal', 'deep'] as const).map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setIntensity(lvl)}
                  className={`py-1.5 text-xs font-medium rounded-8 border capitalize transition-colors ${
                    intensity === lvl
                      ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 text-zinc-600'
                  }`}
                >
                  {lvl} ({lvl === 'quick' ? 'Smoke' : lvl === 'normal' ? 'Standard' : 'Thorough'})
                </button>
              ))}
            </div>
          </div>
        </Card>
      )}

      {/* STEP 5: REVIEW & LAUNCH */}
      {step === 5 && (
        <Card className="p-6 space-y-5">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Review & Launch Session</h2>

          <Input
            label="Session Name"
            value={sessionName}
            onChange={(e) => setSessionName(e.target.value)}
            className="text-sm font-medium"
          />

          <div className="rounded-12 border border-zinc-200 dark:border-zinc-800 p-4 space-y-3 bg-zinc-50 dark:bg-zinc-950">
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Execution Mode:</span>
              <span className="font-semibold uppercase text-brand-600">{mode}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Target Base URL:</span>
              <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-200">{baseUrl}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Pipeline Type:</span>
              <span className="font-semibold">{agentic ? 'Autonomous Agentic (SSE)' : 'Linear Pipeline'}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Categories:</span>
              <span className="font-semibold">{categories.join(', ')}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Intensity:</span>
              <span className="font-semibold capitalize">{intensity}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Primary Auth:</span>
              <span className="font-semibold capitalize">{authType}</span>
            </div>
          </div>

          <Button
            onClick={handleStartSession}
            loading={launching}
            className="w-full py-3 text-base"
          >
            <RocketLaunch className="w-5 h-5" />
            <span>Start Test Session</span>
          </Button>
        </Card>
      )}

      {/* Wizard Navigation Footer */}
      <div className="flex items-center justify-between pt-2">
        {step > 1 ? (
          <Button variant="secondary" onClick={() => setStep(step - 1)}>
            <ArrowLeft className="w-4 h-4" />
            <span>Previous</span>
          </Button>
        ) : <div />}

        {step < 5 && (
          <Button onClick={() => setStep(step + 1)}>
            <span>Next</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
