import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

let refreshPromise: Promise<void> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config
    if (error.response?.status === 401 && request && !request._retry && !request.url?.includes('/auth/refresh')) {
      request._retry = true
      try {
        refreshPromise ??= api.post('/auth/refresh').then(() => undefined).finally(() => {
          refreshPromise = null
        })
        await refreshPromise
        return api(request)
      } catch {
        // Preserve the original request failure; AuthProvider will clear its
        // user state on the next protected request.
      }
    }
    return Promise.reject(error)
  }
)
