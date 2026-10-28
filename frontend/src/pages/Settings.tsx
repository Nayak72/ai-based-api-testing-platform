import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { authApi, providersApi, ProviderProfile } from '../api/endpoints'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Modal } from '../components/ui/Modal'
import {
  User,
  Lock,
  Cpu,
  Bell,
  Sliders,
  FloppyDisk,
  Plus,
  Trash,
  CheckCircle,
  Lightning,
} from '@phosphor-icons/react'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

type SettingsTab = 'profile' | 'security' | 'ai' | 'execution' | 'notifications'

export function Settings() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')

  // Profile Form
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileSaving, setProfileSaving] = useState(false)

  // Security Form
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [securitySaving, setSecuritySaving] = useState(false)

  // Provider Profiles
  const [profiles, setProfiles] = useState<ProviderProfile[]>([])
  const [loadingProfiles, setLoadingProfiles] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)

  // Profile Create Form
  const [newProfileName, setNewProfileName] = useState('')
  const [newProviderType, setNewProviderType] = useState('openrouter')
  const [newBaseUrl, setNewBaseUrl] = useState('https://openrouter.ai/api/v1')
  const [newModel, setNewModel] = useState('anthropic/claude-3.5-sonnet')
  const [newApiKey, setNewApiKey] = useState('')
  const [creatingProfile, setCreatingProfile] = useState(false)

  const fetchProfiles = async () => {
    setLoadingProfiles(true)
    try {
      const res = await providersApi.list()
      const list: ProviderProfile[] = Array.isArray(res.data)
        ? res.data
        : (res.data as any)?.providers ?? []
      setProfiles(list)
    } catch {
      toast.error('Failed to load provider profiles')
    } finally {
      setLoadingProfiles(false)
    }
  }

  useEffect(() => {
    fetchProfiles()
  }, [])

  // Execution Defaults
  const [defaultConcurrency, setDefaultConcurrency] = useState(parseInt(localStorage.getItem('default_concurrency') || '10'))
  const [defaultTimeout, setDefaultTimeout] = useState(parseInt(localStorage.getItem('default_timeout') || '30'))
  const [defaultRetries, setDefaultRetries] = useState(parseInt(localStorage.getItem('default_retries') || '1'))
  const [defaultReportFormat, setDefaultReportFormat] = useState(localStorage.getItem('default_report_format') || 'html')

  // Notification Preferences
  const [notifyOnCompletion, setNotifyOnCompletion] = useState(localStorage.getItem('notify_completion') !== 'false')
  const [notifyOnFailure, setNotifyOnFailure] = useState(localStorage.getItem('notify_failure') !== 'false')
  const [notifyOnVulnerability, setNotifyOnVulnerability] = useState(localStorage.getItem('notify_vulnerability') !== 'false')
  const [webhookUrl, setWebhookUrl] = useState(localStorage.getItem('webhook_url') || '')

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setProfileSaving(true)
    try {
      await authApi.updateMe({ full_name: fullName })
      toast.success('Profile updated successfully')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setProfileSaving(false)
    }
  }

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    setSecuritySaving(true)
    try {
      await authApi.updateMe({ password: newPassword })
      toast.success('Password changed successfully')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setSecuritySaving(false)
    }
  }

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreatingProfile(true)
    try {
      await providersApi.create({
        name: newProfileName,
        provider_type: newProviderType,
        base_url: newBaseUrl,
        default_model: newModel,
        api_key: newApiKey || undefined,
      })
      toast.success('Provider profile created')
      setModalOpen(false)
      setNewProfileName('')
      setNewApiKey('')
      fetchProfiles()
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create provider')
    } finally {
      setCreatingProfile(false)
    }
  }

  const handleDeleteProfile = async (id: string) => {
    if (!confirm('Are you sure you want to delete this provider profile?')) return
    try {
      await providersApi.delete(id)
      toast.success('Profile deleted')
      fetchProfiles()
    } catch {
      toast.error('Failed to delete profile')
    }
  }

  const handleTestProfile = async (id: string) => {
    setTestingId(id)
    try {
      const res = await providersApi.test(id)
      if (res.data.ok) {
        toast.success(`Connected! Latency: ${res.data.latency_ms}ms`)
      } else {
        toast.error(`Connection failed: ${res.data.message}`)
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Test connection error')
    } finally {
      setTestingId(null)
    }
  }

  const handleProviderTypePreset = (type: string) => {
    setNewProviderType(type)
    if (type === 'openrouter') {
      setNewBaseUrl('https://openrouter.ai/api/v1')
      setNewModel('anthropic/claude-3.5-sonnet')
    } else if (type === 'nim') {
      setNewBaseUrl('https://integrate.api.nvidia.com/v1')
      setNewModel('meta/llama-3.1-70b-instruct')
    } else if (type === 'ollama') {
      setNewBaseUrl('http://localhost:11434/v1')
      setNewModel('llama3')
    } else if (type === 'lmstudio') {
      setNewBaseUrl('http://localhost:1234/v1')
      setNewModel('default')
    } else if (type === 'llamacpp') {
      setNewBaseUrl('http://localhost:8080/v1')
      setNewModel('default')
    }
  }

  const handleSaveExecutionSettings = (e: React.FormEvent) => {
    e.preventDefault()
    localStorage.setItem('default_concurrency', defaultConcurrency.toString())
    localStorage.setItem('default_timeout', defaultTimeout.toString())
    localStorage.setItem('default_retries', defaultRetries.toString())
    localStorage.setItem('default_report_format', defaultReportFormat)
    toast.success('Execution preferences saved')
  }

  const handleSaveNotificationSettings = (e: React.FormEvent) => {
    e.preventDefault()
    localStorage.setItem('notify_completion', notifyOnCompletion.toString())
    localStorage.setItem('notify_failure', notifyOnFailure.toString())
    localStorage.setItem('notify_vulnerability', notifyOnVulnerability.toString())
    localStorage.setItem('webhook_url', webhookUrl)
    toast.success('Notification preferences saved')
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'ai', label: 'AI Providers', icon: Cpu },
    { id: 'execution', label: 'Execution Defaults', icon: Sliders },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ] as const

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Settings</h1>
        <p className="text-zinc-500 dark:text-zinc-400 mt-1">
          Manage your account preferences, AI integrations, and testing defaults
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Navigation Sidebar */}
        <div className="space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as SettingsTab)}
                className={clsx(
                  'w-full flex items-center gap-3 px-3.5 py-2.5 rounded-12 text-sm font-medium transition-colors text-left',
                  active
                    ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300 font-semibold'
                    : 'text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
                )}
              >
                <Icon className={clsx('h-5 w-5', active ? 'text-brand-600 dark:text-brand-400' : 'text-zinc-400')} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        {/* Tab Content */}
        <div className="md:col-span-3 space-y-6">
          {activeTab === 'profile' && (
            <Card>
              <CardHeader>
                <CardTitle>Profile Details</CardTitle>
                <CardDescription>Update your personal display information</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdateProfile} className="space-y-4">
                  <Input
                    label="Email Address"
                    value={user?.email || ''}
                    disabled
                    helperText="Email cannot be changed directly"
                  />
                  <Input
                    label="Full Name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                  />
                  <div className="pt-2 flex justify-end">
                    <Button type="submit" loading={profileSaving}>
                      <FloppyDisk className="h-4 w-4" />
                      Save Profile
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle>Security & Password</CardTitle>
                <CardDescription>Change your account password securely</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdatePassword} className="space-y-4">
                  <Input
                    label="New Password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                  <Input
                    label="Confirm New Password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                  />
                  <div className="pt-2 flex justify-end">
                    <Button type="submit" loading={securitySaving}>
                      <Lock className="h-4 w-4" />
                      Update Password
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'ai' && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>AI Provider Profiles</CardTitle>
                  <CardDescription>
                    Configure Cloud (OpenRouter, NIM) and Local (Ollama, LM Studio) AI connections. API keys are encrypted server-side and never stored in localStorage.
                  </CardDescription>
                </div>
                <Button size="sm" onClick={() => setModalOpen(true)}>
                  <Plus className="h-4 w-4" />
                  Add Provider
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {profiles.length === 0 && !loadingProfiles && (
                    <div className="text-center p-8 border border-dashed rounded-16 border-zinc-200 dark:border-zinc-800 text-zinc-400">
                      <Cpu className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No provider profiles configured yet.</p>
                      <p className="text-xs text-zinc-500 mt-1">
                        Add an OpenRouter, NIM, or local Ollama profile to get started.
                      </p>
                    </div>
                  )}

                  {profiles.map((p) => (
                    <div
                      key={p.id}
                      className="p-4 rounded-16 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-zinc-900 dark:text-zinc-100 text-sm">
                            {p.name}
                          </span>
                          <span className="px-2 py-0.5 rounded-6 text-[11px] font-bold uppercase bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
                            {p.provider_type}
                          </span>
                          {p.has_key ? (
                            <span className="text-[11px] text-zinc-500 flex items-center gap-1 font-mono">
                              <CheckCircle className="w-3 h-3 text-brand-600" /> Key encrypted
                            </span>
                          ) : (
                            <span className="text-[11px] text-zinc-400 font-mono">No key (Local)</span>
                          )}
                        </div>
                        <p className="text-xs font-mono text-zinc-500 mt-1">
                          Model: <span className="font-semibold text-zinc-700 dark:text-zinc-300">{p.default_model}</span> • Base: {p.base_url}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleTestProfile(p.id)}
                          loading={testingId === p.id}
                        >
                          <Lightning className="h-3.5 w-3.5 text-brand-600" />
                          <span>Test</span>
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteProfile(p.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'execution' && (
            <Card>
              <CardHeader>
                <CardTitle>Execution Defaults</CardTitle>
                <CardDescription>Default concurrency and timeout parameters for test executions</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveExecutionSettings} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="Default Concurrency (Requests in parallel)"
                      type="number"
                      value={defaultConcurrency}
                      onChange={(e) => setDefaultConcurrency(parseInt(e.target.value))}
                      min={1}
                      max={50}
                    />
                    <Input
                      label="Request Timeout (Seconds)"
                      type="number"
                      value={defaultTimeout}
                      onChange={(e) => setDefaultTimeout(parseInt(e.target.value))}
                      min={5}
                      max={120}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="Max Retries"
                      type="number"
                      value={defaultRetries}
                      onChange={(e) => setDefaultRetries(parseInt(e.target.value))}
                      min={0}
                      max={5}
                    />
                    <div>
                      <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
                        Default Report Format
                      </label>
                      <select
                        value={defaultReportFormat}
                        onChange={(e) => setDefaultReportFormat(e.target.value)}
                        className="w-full rounded-12 border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      >
                        <option value="html">HTML Report</option>
                        <option value="pdf">PDF Document</option>
                        <option value="both">Both (HTML & PDF)</option>
                      </select>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <Button type="submit">
                      <FloppyDisk className="h-4 w-4" />
                      Save Defaults
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'notifications' && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Choose how and when you receive automated testing alerts</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveNotificationSettings} className="space-y-5">
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifyOnCompletion}
                        onChange={(e) => setNotifyOnCompletion(e.target.checked)}
                        className="w-4 h-4 text-brand-600 rounded-4 border-zinc-300 focus:ring-brand-500"
                      />
                      <div>
                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Test Run Completion</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">Receive alerts when test suites finish execution</p>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifyOnFailure}
                        onChange={(e) => setNotifyOnFailure(e.target.checked)}
                        className="w-4 h-4 text-brand-600 rounded-4 border-zinc-300 focus:ring-brand-500"
                      />
                      <div>
                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">Test Failure Alerts</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">Notify immediately when assertions fail</p>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifyOnVulnerability}
                        onChange={(e) => setNotifyOnVulnerability(e.target.checked)}
                        className="w-4 h-4 text-brand-600 rounded-4 border-zinc-300 focus:ring-brand-500"
                      />
                      <div>
                        <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">High Risk Vulnerability Detection</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">Alert when LLM analyzer flags critical or high security risks</p>
                      </div>
                    </label>
                  </div>

                  <Input
                    label="Webhook / Slack URL (Optional)"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                    helperText="Webhook payload will be dispatched on test completion"
                  />

                  <div className="pt-2 flex justify-end">
                    <Button type="submit">
                      <FloppyDisk className="h-4 w-4" />
                      Save Preferences
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Modal: Add Provider Profile */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add AI Provider Profile"
        description="Configure a new LLM provider profile for autonomous test generation."
        size="md"
      >
        <form onSubmit={handleCreateProfile} className="space-y-4">
          <Input
            label="Profile Name"
            value={newProfileName}
            onChange={(e) => setNewProfileName(e.target.value)}
            placeholder="e.g. Claude 3.5 Sonnet (OpenRouter)"
            required
          />

          <div>
            <label className="block text-xs font-medium text-zinc-600 dark:text-zinc-400 mb-1">
              Provider Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'openrouter', label: 'OpenRouter' },
                { id: 'nim', label: 'NVIDIA NIM' },
                { id: 'ollama', label: 'Local Ollama' },
                { id: 'lmstudio', label: 'LM Studio' },
                { id: 'llamacpp', label: 'llama.cpp' },
                { id: 'openai_compatible', label: 'OpenAI API' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => handleProviderTypePreset(t.id)}
                  className={`py-1.5 text-xs font-medium rounded-8 border transition-colors ${
                    newProviderType === t.id
                      ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950/40 dark:text-brand-300'
                      : 'border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 text-zinc-600'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Base URL"
            value={newBaseUrl}
            onChange={(e) => setNewBaseUrl(e.target.value)}
            placeholder="https://openrouter.ai/api/v1"
            className="font-mono text-xs"
            required
          />

          <Input
            label="Default Model"
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
            placeholder="anthropic/claude-3.5-sonnet"
            className="font-mono text-xs"
            required
          />

          <Input
            label="API Key (Optional for local Ollama)"
            type="password"
            value={newApiKey}
            onChange={(e) => setNewApiKey(e.target.value)}
            placeholder="sk-or-... (Stored encrypted server-side)"
            className="font-mono text-xs"
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={creatingProfile}>
              Save Profile
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
