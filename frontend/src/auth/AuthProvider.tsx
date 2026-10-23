import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api/client'
import { User } from '../api/endpoints'

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const response = await api.get('/auth/me')
      setUser(response.data)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    const { access_token } = response.data
    localStorage.setItem('access_token', access_token)
    api.defaults.headers.common.Authorization = `Bearer ${access_token}`
    await refreshUser()
  }

  const register = async (email: string, password: string, fullName?: string) => {
    const response = await api.post('/auth/register', { email, password, full_name: fullName })
    const { access_token } = response.data
    localStorage.setItem('access_token', access_token)
    api.defaults.headers.common.Authorization = `Bearer ${access_token}`
    await refreshUser()
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      localStorage.removeItem('access_token')
      delete api.defaults.headers.common.Authorization
      setUser(null)
    }
  }

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      refreshUser()
    } else {
      setLoading(false)
    }
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}