import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, Button, Input, ErrorState, Skeleton } from '../components/ui'
import {
  specsApi,
  catalogApi,
  providersApi,
  sessionsApi,
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

type SourceType = 'catalog' | 'vulnshop' | 'existing' | 'url'

export function NewSession() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)

  // Step 1: Mode
  const [mode, setMode] = useState<'local' | 'online'>('local')

  // Step 2: Spec source
  const [sourceType, setSourceType] = useState<SourceType>('vulnshop')
  const [selectedSpecId, setSelectedSpecId] = useState<string>('')
  const [selectedCatalogId, setSelectedCatalogId] = useState<string>('')
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
  const [selectedProviderId, setSelectedProviderId] = useState<string>('')
  const agentic = true

  // Step 5: Scope & Intensity
  const [categories, setCategories] = useState<string[]>(['functional', 'edge', 'malformed', 'security'])
  const [intensity, setIntensity] = useState<'safe' | 'standard' | 'aggressive'>('standard')

  // Launch state
  const [launching, setLaunching] = useState(false)
  const [sessionName, setSessionName] = useState('Security & Functional Audit')
  const [stepErrors, setStepErrors] = useState<Record<number, string>>({})
  const firstInvalidRef = useRef<HTMLDivElement>(null)
  const specsQuery = useQuery({ queryKey: ['specs', 'session-picker'], queryFn: () => specsApi.list({ page_size: 100 }) })
  const catalogQuery = useQuery({ queryKey: ['catalog'], queryFn: () => catalogApi.list() })
  const providersQuery = useQuery({ queryKey: ['providers'], queryFn: () => providersApi.list() })
  const specs = useMemo(() => specsQuery.data?.data.specs ?? [], [specsQuery.data])
  const catalogItems = useMemo(() => catalogQuery.data?.data.entries ?? [], [catalogQuery.data])
  const providers = useMemo(() => providersQuery.data?.data.providers ?? [], [providersQuery.data])
  const optionLoading = specsQuery.isLoading || catalogQuery.isLoading || providersQuery.isLoading
  const optionError = specsQuery.isError || catalogQuery.isError || providersQuery.isError

  useEffect(() => {
    const defaultProvider = providers.find((provider) => provider.is_default)
    if (!selectedProviderId && defaultProvider) setSelectedProviderId(defaultProvider.id)
  }, [providers, selectedProviderId])

  useEffect(() => {
    if (Object.keys(stepErrors).length) firstInvalidRef.current?.focus()
  }, [stepErrors])

  const handleSourceChange = (type: SourceType) => {
    setSourceType(type)
    setSelectedSpecId('')
    setStepErrors((errors) => ({ ...errors, 2: '' }))
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
      await specsQuery.refetch()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Import failed')
    } finally {
      setImportingUrl(false)
    }
  }

  const toggleCategory = (cat: string) => {
    if (cat === 'security' && mode === 'online' && !ownedAttestation) return
    setCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    )
  }

  const validateStep = (currentStep: number): string | null => {
    if (currentStep === 1 && !mode) return 'Choose a local or online execution mode.'
    if (currentStep === 2) {
      if (sourceType === 'catalog' && !selectedCatalogId) return 'Choose a public catalog entry before continuing.'
      if (sourceType === 'existing' && !selectedSpecId) return 'Choose a ready specification before continuing.'
      if (sourceType === 'url') return 'Import the specification from its URL before continuing.'
      if (!baseUrl.trim()) return 'Enter the target base URL for this session.'
    }
    if (currentStep === 3 && mode === 'online' && categories.includes('security') && !ownedAttestation) return 'Confirm you are authorized before enabling online security testing.'
    if (currentStep === 4 && categories.length === 0) return 'Select at least one test category.'
    return null
  }

  const moveToStep = (nextStep: number) => {
    if (nextStep > step) {
      const error = validateStep(step)
      if (error) {
        setStepErrors((errors) => ({ ...errors, [step]: error }))
        return
      }
    }
    setStepErrors((errors) => ({ ...errors, [step]: '' }))
    setStep(nextStep)
  }

  const handleStartSession = async () => {
    const error = validateStep(4)
    if (error || !sessionName.trim()) {
      setStepErrors((errors) => ({ ...errors, 5: error ?? 'Enter a name for this session.' }))
      return
    }
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
          const res = await catalogApi.import('vulnshop')
          finalSpecId = res.data.spec_id
        }
      } else if (sourceType === 'catalog') {
        // Import catalog spec
        if (!selectedCatalogId) {
          toast.error('Select a catalog entry first')
          return
        }
        const res = await catalogApi.import(selectedCatalogId)
        finalSpecId = res.data.spec_id
      }

      if (!finalSpecId) {
        toast.error('Please select or import a specification first')
        return
      }

      if (!sessionName.trim() || categories.length === 0) {
        toast.error('Provide a session name and select at least one category')
        return
      }
      if (mode === 'online' && categories.includes('security') && !ownedAttestation) {
        toast.error('Online security testing requires ownership attestation')
        return
      }

      const res = await sessionsApi.create({
        spec_id: finalSpecId,
        name: sessionName.trim(),
        mode,
        base_url: baseUrl || undefined,
        auth_type: authType === 'none' ? undefined : authType,
        auth_token: authToken || undefined,
        secondary_auth_type: secondaryAuthType === 'none' ? undefined : secondaryAuthType,
        secondary_auth_token: secondaryAuthToken || undefined,
        provider_profile_id: selectedProviderId || undefined,
        categories,
        intensity,
        owned_host_attestation: ownedAttestation,
        agentic,
      })

      toast.success('Test Session initiated!')
      navigate(`/sessions/${res.data.session_id || res.data.id}`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to start session')
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 page-enter">
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

      {optionError && <ErrorState title="Session options could not be loaded" description="Specifications, catalog entries, or provider profiles may be unavailable. Retry before configuring a dependent option." onRetry={() => { void specsQuery.refetch(); void catalogQuery.refetch(); void providersQuery.refetch() }} />}

      {/* Stepper Progress */}
      <ol className="grid grid-cols-5 gap-2 border-b border-slate-200 pb-4 dark:border-slate-800" aria-label="Session setup progress">
        {[
          { num: 1, label: 'Mode' },
          { num: 2, label: 'Target & Spec' },
          { num: 3, label: 'Auth & Safety' },
          { num: 4, label: 'AI Strategy' },
          { num: 5, label: 'Review & Launch' },
        ].map((s) => (
          <li key={s.num} className="flex min-w-0 items-center gap-2">
            <button
              type="button"
              onClick={() => s.num < step && moveToStep(s.num)}
              disabled={s.num > step}
              aria-current={step === s.num ? 'step' : undefined}
              aria-label={`Step ${s.num}: ${s.label}${step > s.num ? ', complete' : step === s.num ? ', current' : ''}`}
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                step === s.num
                  ? 'bg-brand-600 text-white'
                  : step > s.num
                  ? 'bg-brand-100 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300'
                  : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'
              }`}
            >
              {step > s.num ? '✓' : s.num}
            </button>
            <span
              className={`text-xs font-medium hidden sm:inline ${
                step === s.num ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-400'
              }`}
            >
              {s.label}
            </span>
          </li>
        ))}
      </ol>

      {stepErrors[step] && <div ref={firstInvalidRef} tabIndex={-1} role="alert" className="rounded-12 border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 outline-none dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200">{stepErrors[step]}</div>}

      {/* STEP 1: MODE */}
      {step === 1 && (
        <div className="space-y-4">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Select Execution Mode</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2" role="radiogroup" aria-label="Execution mode">
            <button
              type="button"
              role="radio"
              aria-checked={mode === 'local'}
              onClick={() => {
                setMode('local')
                setBaseUrl('http://localhost:8001')
              }}
              className={`p-6 rounded-16 border-2 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
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
            </button>

            <button
              type="button"
              role="radio"
              aria-checked={mode === 'online'}
              onClick={() => {
                setMode('online')
                setBaseUrl('')
                setCategories((current) => current.filter((category) => category !== 'security'))
              }}
              className={`p-6 rounded-16 border-2 text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
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
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: SPEC SOURCE */}
      {step === 2 && (
        <Card className="p-6 space-y-5">
          <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">API Target & Specification</h2>

          {optionLoading && <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{[1, 2, 3, 4].map((item) => <Skeleton key={item} className="h-20 w-full" />)}</div>}

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
                  onClick={() => handleSourceChange(s.id as SourceType)}
                  role="radio"
                  aria-checked={sourceType === s.id}
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
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Public catalog entry">
                {catalogItems.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    role="radio"
                    aria-checked={selectedCatalogId === item.id}
                    onClick={() => {
                      setSelectedCatalogId(item.id)
                      setBaseUrl(item.base_url)
                      setSessionName(`${item.name} Assessment`)
                    }}
                    className={`p-3 rounded-12 border text-left transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                      selectedCatalogId === item.id
                        ? 'border-brand-600 bg-brand-50/40 dark:bg-brand-950/20'
                        : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50'
                    }`}
                  >
                    <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100">{item.name}</p>
                    <p className="text-[11px] text-zinc-500 font-mono mt-0.5 truncate">{item.base_url}</p>
                  </button>
                ))}
              </div>
              {!catalogQuery.isLoading && catalogItems.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No public catalog entries are available from this server.</p>}
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
                <option value="">Select a ready specification</option>
                {specs.filter((s) => s.status === 'ready').map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.endpoints_count} endpoints)
                  </option>
                ))}
              </select>
              {!specsQuery.isLoading && specs.filter((s) => s.status === 'ready').length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400">No ready specifications are available. Upload or import one to continue.</p>}
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
              helperText="This is the effective target URL. It is set by the selected source and can be changed intentionally."
              placeholder={mode === 'local' ? 'http://localhost:8001' : 'https://api.example.com'}
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
                  onChange={(e) => {
                    setOwnedAttestation(e.target.checked)
                    if (!e.target.checked) setCategories((current) => current.filter((category) => category !== 'security'))
                  }}
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
            <span className="mt-1 text-xs font-semibold text-brand-700">Required</span>
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
              ].map((c) => {
                const unavailable = c.id === 'security' && mode === 'online' && !ownedAttestation
                return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => toggleCategory(c.id)}
                  disabled={unavailable}
                  aria-describedby={unavailable ? 'security-category-help' : undefined}
                  className={`p-2.5 rounded-8 text-xs font-semibold border transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                    categories.includes(c.id)
                      ? 'border-brand-600 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 text-zinc-400 hover:bg-zinc-50'
                  }`}
                >
                  {categories.includes(c.id) ? '✓ ' : '+ '}
                  {c.label}
                </button>
                )
              })}
            </div>
            {mode === 'online' && !ownedAttestation && <p id="security-category-help" className="text-xs text-amber-700 dark:text-amber-300">OWASP security tests are unavailable until you confirm authorization for this online target.</p>}
          </div>

          {/* Intensity */}
          <div className="space-y-2 pt-2 border-t border-zinc-100 dark:border-zinc-800">
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400">
              Test Intensity
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(['safe', 'standard', 'aggressive'] as const).map((lvl) => (
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
                  {lvl} ({lvl === 'safe' ? 'Smoke' : lvl === 'standard' ? 'Standard' : 'Thorough'})
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
              <span className="font-semibold capitalize">{authType === 'none' ? 'Not configured' : `${authType.replace('_', ' ')} configured`}</span>
            </div>
            <div className="flex justify-between gap-4 text-xs">
              <span className="text-zinc-500">Secondary identity:</span>
              <span className="font-semibold capitalize">{secondaryAuthType === 'none' ? 'Not configured' : `${secondaryAuthType.replace('_', ' ')} configured`}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-zinc-500">Authorization:</span>
              <span className="font-semibold">{mode === 'online' ? (ownedAttestation ? 'Attested' : 'Not attested') : 'Local mode policy'}</span>
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
          <Button variant="secondary" onClick={() => moveToStep(step - 1)}>
            <ArrowLeft className="w-4 h-4" />
            <span>Previous</span>
          </Button>
        ) : <div />}

        {step < 5 && (
          <Button onClick={() => moveToStep(step + 1)}>
            <span>Next</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
