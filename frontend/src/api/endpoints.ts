import { api } from './client'

export interface User {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  created_at: string
  last_login: string | null
  ai_settings?: {
    primary_provider?: string
    default_model?: string
    openrouter_api_key?: string
    nim_api_key?: string
  }
}

export interface Spec {
  id: string
  name: string
  source_type: string
  source_format: string
  endpoints_count: number
  spec_version: string | null
  base_url: string | null
  status: string
  parse_error: string | null
  created_at: string
  updated_at: string
}

export interface SpecDetail extends Spec {
  raw_content: string
  parsed_spec: any
  auth_config: any | null
}

export interface Endpoint {
  endpoint_id: string
  method: string
  path: string
  summary: string | null
  description: string | null
  parameters: any[]
  request_body: any | null
  responses: Record<string, any>
  security: any[]
}

export interface TestCase {
  id: string
  spec_id: string
  endpoint_id: string
  category: string
  subcategory: string
  title: string
  description: string
  request: {
    method: string
    path: string
    headers: Record<string, string>
    query_params: Record<string, any>
    body: any
  }
  expected: {
    status_code: number
    response_schema: any | null
    assertions: any[]
  }
  metadata: {
    owasp_category: string | null
    severity: string
    generated_by: string
    generation_prompt_hash: string
    tokens_used: number
    request_hash: string
  }
  created_at: string
}

export interface Run {
  id: string
  spec_id: string
  user_id: string
  name: string
  trigger: string
  status: string
  config: {
    concurrency: number
    timeout_seconds: number
    retry_failed: number
    categories: string[]
    base_url_override: string | null
    auth_override: any | null
  }
  summary: {
    total: number
    passed: number
    failed: number
    errors: number
    skipped: number
    duration_seconds: number
  }
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface Result {
  id: string
  run_id: string
  test_case_id: string
  endpoint_id: string
  category: string
  status: string
  request_sent: {
    method: string
    url: string
    headers: Record<string, string>
    body: any
  }
  response: {
    status_code: number
    headers: Record<string, string>
    body: any
    body_truncated: boolean
    body_hash: string | null
    duration_ms: number
  }
  assertions: Array<{
    assertion: any
    result: boolean
  }>
  error: string | null
  llm_analysis: any | null
  retried: boolean
  attempt: number
  created_at: string
}

export interface Report {
  id: string
  run_id: string
  user_id: string
  format: string
  html_path: string | null
  pdf_path: string | null
  generated_at: string
  file_size_bytes: number
}

// Auth
export const authApi = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  register: (email: string, password: string, full_name?: string) => api.post('/auth/register', { email, password, full_name }),
  refresh: (refresh_token: string) => api.post('/auth/refresh', { refresh_token }),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<User>('/auth/me'),
  updateMe: (data: { full_name?: string; password?: string; ai_settings?: Record<string, any> }) => api.patch<User>('/auth/me', data),
}

// Specs
export const specsApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get<{ specs: Spec[]; total: number; page: number; page_size: number }>('/specs', { params }),
  upload: (file: File, data: { name: string; source_type: string; source_format: string; auth_type?: string; auth_token_env_var?: string }) => {
    const formData = new FormData()
    formData.append('file', file)
    Object.entries(data).forEach(([key, value]) => {
      if (value) formData.append(key, value)
    })
    return api.post<Spec>('/specs', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  get: (specId: string) => api.get<SpecDetail>(`/specs/${specId}`),
  parse: (specId: string) => api.post<Spec>(`/specs/${specId}/parse`),
  endpoints: (specId: string) => api.get<{ spec_id: string; endpoints: Endpoint[]; total: number }>(`/specs/${specId}/endpoints`),
  delete: (specId: string) => api.delete(`/specs/${specId}`),
}

// Test Cases
export const testCasesApi = {
  generate: (specId: string, data: {
    categories?: string[]
    prompt_version?: string
    dry_run?: boolean
    model?: string
    provider?: string
    api_key?: string
  }) => api.post(`/specs/${specId}/test-cases/generate`, data),
  list: (specId: string, params?: { endpoint_id?: string; category?: string; page?: number; page_size?: number }) =>
    api.get<{ test_cases: TestCase[]; total: number; page: number; page_size: number }>(`/specs/${specId}/test-cases`, { params }),
  get: (specId: string, testCaseId: string) => api.get<TestCase>(`/specs/${specId}/test-cases/${testCaseId}`),
  update: (specId: string, testCaseId: string, data: Partial<TestCase>) => api.patch<TestCase>(`/specs/${specId}/test-cases/${testCaseId}`, data),
  delete: (specId: string, testCaseId: string) => api.delete(`/specs/${specId}/test-cases/${testCaseId}`),
}

// Runs
export const runsApi = {
  create: (data: { spec_id: string; name: string; config?: any }) => api.post<Run>('/runs', data),
  list: (params?: { spec_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get<{ runs: Run[]; total: number; page: number; page_size: number }>('/runs', { params }),
  get: (runId: string) => api.get<Run>(`/runs/${runId}`),
  results: (runId: string, params?: { status?: string; category?: string; page?: number; page_size?: number }) =>
    api.get<{ results: Result[]; total: number; page: number; page_size: number }>(`/runs/${runId}/results`, { params }),
  result: (runId: string, resultId: string) => api.get<Result>(`/runs/${runId}/results/${resultId}`),
  cancel: (runId: string) => api.post<Run>(`/runs/${runId}/cancel`),
  retryFailed: (runId: string) => api.post<Run>(`/runs/${runId}/retry-failed`),
  analyze: (runId: string) => api.post(`/runs/${runId}/analyze`),
}

// Reports
export const reportsApi = {
  generate: (runId: string, format: 'html' | 'pdf' | 'both') => api.post('/reports', { run_id: runId, format }),
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<{ reports: Report[]; total: number; page: number; page_size: number }>('/reports', { params }),
  get: (reportId: string) => api.get<Report>(`/reports/${reportId}`),
  download: (reportId: string, format: 'html' | 'pdf') => api.get(`/reports/${reportId}/download`, { params: { format }, responseType: 'blob' }),
  getByRun: (runId: string) => api.get<Report>(`/reports/runs/${runId}`),
}