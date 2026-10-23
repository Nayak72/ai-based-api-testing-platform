import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/endpoints'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { User, Lock, Cpu, Bell, Sliders, Eye, EyeSlash, FloppyDisk } from '@phosphor-icons/react'
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
  const [showPassword, setShowPassword] = useState(false)
  const [securitySaving, setSecuritySaving] = useState(false)

  // AI Settings
  const [openRouterKey, setOpenRouterKey] = useState(localStorage.getItem('openrouter_api_key') || user?.ai_settings?.openrouter_api_key || '')
  const [nimKey, setNimKey] = useState(localStorage.getItem('nim_api_key') || user?.ai_settings?.nim_api_key || '')
  const [primaryProvider, setPrimaryProvider] = useState(localStorage.getItem('ai_primary_provider') || user?.ai_settings?.primary_provider || 'openrouter')
  const [defaultModel, setDefaultModel] = useState(localStorage.getItem('ai_default_model') || user?.ai_settings?.default_model || 'meta-llama/llama-3.3-70b-instruct:free')
  const [aiSaving, setAiSaving] = useState(false)

  useEffect(() => {
    if (user?.ai_settings) {
      if (!localStorage.getItem('ai_default_model') && user.ai_settings.default_model) {
        setDefaultModel(user.ai_settings.default_model)
      }
      if (!localStorage.getItem('ai_primary_provider') && user.ai_settings.primary_provider) {
        setPrimaryProvider(user.ai_settings.primary_provider)
      }
      if (!localStorage.getItem('openrouter_api_key') && user.ai_settings.openrouter_api_key) {
        setOpenRouterKey(user.ai_settings.openrouter_api_key)
      }
      if (!localStorage.getItem('nim_api_key') && user.ai_settings.nim_api_key) {
        setNimKey(user.ai_settings.nim_api_key)
      }
    }
  }, [user])

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

  const handleSaveAiSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setAiSaving(true)
    localStorage.setItem('openrouter_api_key', openRouterKey)
    localStorage.setItem('nim_api_key', nimKey)
    localStorage.setItem('ai_primary_provider', primaryProvider)
    localStorage.setItem('ai_default_model', defaultModel)

    try {
      await authApi.updateMe({
        ai_settings: {
          primary_provider: primaryProvider,
          default_model: defaultModel,
          openrouter_api_key: openRouterKey,
          nim_api_key: nimKey,
        },
      })
      toast.success('AI configuration preferences saved')
    } catch {
      toast.success('AI configuration preferences saved locally')
    } finally {
      setAiSaving(false)
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
        <p className="text-zinc-500 dark:text-zinc-400 mt-1">Manage your account preferences, AI integrations, and testing defaults</p>
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

        {/* Content Area */}
        <div className="md:col-span-3">
          {activeTab === 'profile' && (
            <Card>
              <CardHeader>
                <CardTitle>Profile Details</CardTitle>
                <CardDescription>Update your personal information and profile settings</CardDescription>
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
                      Save Changes
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle>Password & Security</CardTitle>
                <CardDescription>Ensure your account is protected with a secure password</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdatePassword} className="space-y-4">
                  <div className="relative">
                    <Input
                      label="New Password"
                      type={showPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="••••••••"
                      helperText="Must be at least 8 characters"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-9 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                    >
                      {showPassword ? <EyeSlash className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                  <Input
                    label="Confirm New Password"
                    type={showPassword ? 'text' : 'password'}
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
              <CardHeader>
                <CardTitle>AI Provider Integrations</CardTitle>
                <CardDescription>Configure custom API keys and provider preferences for test generation and result analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveAiSettings} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Primary AI Provider</label>
                    <select
                      value={primaryProvider}
                      onChange={(e) => setPrimaryProvider(e.target.value)}
                      className="input"
                    >
                      <option value="openrouter">OpenRouter (Claude 3.5 Sonnet / Llama 3)</option>
                      <option value="nim">NVIDIA NIM (Llama 3.1 70B Instruct)</option>
                    </select>
                  </div>

                  <Input
                    label="Default AI Model"
                    type="text"
                    value={defaultModel}
                    onChange={(e) => setDefaultModel(e.target.value)}
                    placeholder="e.g. meta-llama/llama-3.3-70b-instruct:free, mistralai/mistral-7b-instruct:free"
                    helperText="Enter any model name manually. You can specify any free model from OpenRouter (e.g. meta-llama/llama-3.3-70b-instruct:free) or provider model."
                    required
                  />

                  <Input
                    label="OpenRouter API Key"
                    type="password"
                    value={openRouterKey}
                    onChange={(e) => setOpenRouterKey(e.target.value)}
                    placeholder="sk-or-v1-..."
                    helperText="Used for test generation & deep vulnerability analysis"
                  />

                  <Input
                    label="NVIDIA NIM API Key"
                    type="password"
                    value={nimKey}
                    onChange={(e) => setNimKey(e.target.value)}
                    placeholder="nvapi-..."
                    helperText="Used for high-throughput automated test assertions"
                  />

                  <div className="pt-2 flex justify-end">
                    <Button type="submit" loading={aiSaving}>
                      <FloppyDisk className="h-4 w-4" />
                      Save AI Config
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {activeTab === 'execution' && (
            <Card>
              <CardHeader>
                <CardTitle>Execution Defaults</CardTitle>
                <CardDescription>Configure default concurrency, request timeouts, and report formats</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveExecutionSettings} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <Input
                      label="Default Concurrency"
                      type="number"
                      value={defaultConcurrency}
                      onChange={(e) => setDefaultConcurrency(parseInt(e.target.value))}
                      min={1}
                      max={50}
                    />
                    <Input
                      label="Timeout (seconds)"
                      type="number"
                      value={defaultTimeout}
                      onChange={(e) => setDefaultTimeout(parseInt(e.target.value))}
                      min={5}
                      max={300}
                    />
                    <Input
                      label="Max Retries"
                      type="number"
                      value={defaultRetries}
                      onChange={(e) => setDefaultRetries(parseInt(e.target.value))}
                      min={0}
                      max={5}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Default Report Format</label>
                    <select
                      value={defaultReportFormat}
                      onChange={(e) => setDefaultReportFormat(e.target.value)}
                      className="input"
                    >
                      <option value="html">HTML Report</option>
                      <option value="pdf">PDF Document</option>
                      <option value="both">Both (HTML & PDF)</option>
                    </select>
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
    </div>
  )
}
