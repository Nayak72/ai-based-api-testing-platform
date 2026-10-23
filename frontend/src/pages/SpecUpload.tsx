import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useUploadSpec, useParseSpec } from '../hooks/useSpecs'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { UploadSimple, FileText, CaretLeft, CheckCircle, Spinner } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

const SOURCE_TYPES = [
  { value: 'openapi', label: 'OpenAPI/Swagger' },
  { value: 'postman', label: 'Postman Collection' },
]

const SOURCE_FORMATS = [
  { value: 'yaml', label: 'YAML' },
  { value: 'json', label: 'JSON' },
]

export function SpecUpload() {
  const navigate = useNavigate()
  const uploadMutation = useUploadSpec()
  const parseMutation = useParseSpec()

  const [step, setStep] = useState<'upload' | 'parsing' | 'done'>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [sourceType, setSourceType] = useState('openapi')
  const [sourceFormat, setSourceFormat] = useState('yaml')
  const [authType, setAuthType] = useState('bearer')
  const [authTokenEnvVar, setAuthTokenEnvVar] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const [specId, setSpecId] = useState<string | null>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
      if (!name) {
        setName(e.dataTransfer.files[0].name.replace(/\.[^/.]+$/, ''))
      }
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      if (!name) {
        setName(e.target.files[0].name.replace(/\.[^/.]+$/, ''))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      toast.error('Please select a file')
      return
    }
    if (!name.trim()) {
      toast.error('Please enter a name')
      return
    }

    try {
      const response = await uploadMutation.mutateAsync({
        file,
        data: { name, source_type: sourceType, source_format: sourceFormat, auth_type: authType, auth_token_env_var: authTokenEnvVar || undefined },
      })
      setSpecId(response.data.id)
      setStep('parsing')
      await parseMutation.mutateAsync(response.data.id)
      setStep('done')
      toast.success('Specification uploaded and parsed successfully')
      setTimeout(() => navigate(`/specs/${response.data.id}`), 1500)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed')
      setStep('upload')
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/specs" className="p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
          <CaretLeft className="h-6 w-6" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Upload Specification</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Upload an OpenAPI or Postman spec to get started</p>
        </div>
      </div>

      {step === 'upload' && (
        <Card>
          <CardHeader>
            <CardTitle>Upload API Specification</CardTitle>
            <CardDescription>Supported formats: OpenAPI 3.x (YAML/JSON) or Postman Collection v2.1 (JSON)</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div
                className={clsx(
                  'border-2 border-dashed rounded-16 p-8 text-center transition-colors',
                  dragActive ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/10' : 'border-zinc-300 dark:border-zinc-700'
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  id="file-upload"
                  accept=".yaml,.yml,.json"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={uploadMutation.isPending}
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  {!file ? (
                    <>
                      <UploadSimple className="h-12 w-12 text-zinc-400 mx-auto mb-4" />
                      <p className="text-lg font-medium text-zinc-900 dark:text-zinc-50">Drag & drop your spec file here</p>
                      <p className="text-zinc-500 dark:text-zinc-400 mt-1">or click to browse</p>
                      <p className="text-xs text-zinc-400 dark:text-zinc-500 mt-4">Max file size: 10MB</p>
                    </>
                  ) : (
                    <div className="flex items-center justify-center gap-4">
                      <FileText className="h-10 w-10 text-brand-600" />
                      <div className="text-left">
                        <p className="font-medium text-zinc-900 dark:text-zinc-50">{file.name}</p>
                        <p className="text-sm text-zinc-500 dark:text-zinc-400">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                    </div>
                  )}
                </label>
              </div>

              {file && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Specification Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="My API Spec"
                    required
                  />
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Source Type</label>
                    <select
                      value={sourceType}
                      onChange={(e) => setSourceType(e.target.value)}
                      className="input"
                    >
                      {SOURCE_TYPES.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Format</label>
                    <select
                      value={sourceFormat}
                      onChange={(e) => setSourceFormat(e.target.value)}
                      className="input"
                    >
                      {SOURCE_FORMATS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                    </select>
                  </div>
                </div>
              )}

              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-6">
                <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-4">Authentication (Optional)</h3>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
                  Configure authentication for test execution. The token will be resolved from environment variables at runtime.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">Auth Type</label>
                    <select
                      value={authType}
                      onChange={(e) => setAuthType(e.target.value)}
                      className="input"
                    >
                      <option value="bearer">Bearer Token</option>
                      <option value="api_key">API Key</option>
                      <option value="basic">Basic Auth</option>
                    </select>
                  </div>
                  <Input
                    label="Environment Variable Name"
                    value={authTokenEnvVar}
                    onChange={(e) => setAuthTokenEnvVar(e.target.value)}
                    placeholder="e.g., STRIPE_SECRET_KEY"
                    helperText="Name of the environment variable containing the token"
                  />
                </div>
              </div>

              <Button type="submit" className="w-full" loading={uploadMutation.isPending}>
                <UploadSimple className="h-4 w-4" />
                Upload & Parse
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {step === 'parsing' && (
        <Card>
          <CardContent className="text-center py-12">
            <Spinner className="h-12 w-12 text-brand-600 animate-spin mx-auto mb-4" />
            <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">Parsing Specification...</h3>
            <p className="text-zinc-500 dark:text-zinc-400">This may take a moment for large specs</p>
          </CardContent>
        </Card>
      )}

      {step === 'done' && specId && (
        <Card>
          <CardContent className="text-center py-12">
            <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">Specification Ready!</h3>
            <p className="text-zinc-500 dark:text-zinc-400 mb-6">Your API spec has been uploaded and parsed successfully</p>
            <div className="flex justify-center gap-3">
              <Button variant="secondary" onClick={() => { setStep('upload'); setFile(null); setName(''); setSpecId(null); }}>
                Upload Another
              </Button>
              <Link to={`/specs/${specId}`}>
                <Button>View Specification</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}