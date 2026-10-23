import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { SpecsList } from './pages/SpecsList'
import { SpecUpload } from './pages/SpecUpload'
import { SpecDetail } from './pages/SpecDetail'
import { TestCases } from './pages/TestCases'
import { RunDetail } from './pages/RunDetail'
import { RunHistory } from './pages/RunHistory'
import { ReportView } from './pages/ReportView'
import { ReportsList } from './pages/ReportsList'
import { Settings } from './pages/Settings'
import { LoginForm } from './auth/LoginForm'
import { RegisterForm } from './auth/RegisterForm'
import { useAuth } from './hooks/useAuth'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-3 border-brand-500 border-t-transparent"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-3 border-brand-500 border-t-transparent"></div>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><LoginForm /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterForm /></PublicRoute>} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/specs" element={<SpecsList />} />
                <Route path="/specs/upload" element={<SpecUpload />} />
                <Route path="/specs/:specId" element={<SpecDetail />} />
                <Route path="/specs/:specId/test-cases" element={<TestCases />} />
                <Route path="/runs" element={<RunHistory />} />
                <Route path="/runs/:runId" element={<RunDetail />} />
                <Route path="/reports" element={<ReportsList />} />
                <Route path="/reports/:runId" element={<ReportView />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App