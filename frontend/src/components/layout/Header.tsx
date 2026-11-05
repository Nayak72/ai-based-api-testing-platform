import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  List,
  Moon,
  Sun,
  CaretDown,
  User,
  SignOut,
  Gear,
} from '@phosphor-icons/react'
import { useState, useRef, useEffect } from 'react'

const PAGE_TITLES: Array<{ match: (path: string) => boolean; title: string; crumb?: string }> = [
  { match: (path) => path === '/', title: 'Dashboard' },
  { match: (path) => path === '/sessions/new', title: 'New session', crumb: 'Sessions' },
  { match: (path) => /^\/sessions\/[^/]+$/.test(path), title: 'Session detail', crumb: 'Sessions' },
  { match: (path) => path === '/quick-test', title: 'Quick test' },
  { match: (path) => path === '/knowledge-base', title: 'Knowledge base' },
  { match: (path) => path === '/specs/upload', title: 'Upload specification', crumb: 'Specifications' },
  { match: (path) => /\/test-cases$/.test(path), title: 'Test cases', crumb: 'Specifications' },
  { match: (path) => /^\/specs\/[^/]+$/.test(path), title: 'Specification detail', crumb: 'Specifications' },
  { match: (path) => path === '/specs', title: 'Specifications' },
  { match: (path) => /^\/runs\/[^/]+$/.test(path), title: 'Run detail', crumb: 'Test runs' },
  { match: (path) => /^\/runs\/[^/]+\/results\/[^/]+$/.test(path), title: 'Result detail', crumb: 'Test runs' },
  { match: (path) => path === '/runs', title: 'Test runs' },
  { match: (path) => /^\/reports\/[^/]+$/.test(path), title: 'Report detail', crumb: 'Reports' },
  { match: (path) => path === '/reports', title: 'Reports' },
  { match: (path) => path === '/settings', title: 'Settings' },
]

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [darkMode, setDarkMode] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  const profileRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem('theme')
    const isDark = saved === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
    setDarkMode(isDark)
  }, [])

  const toggleDarkMode = () => {
    const newDark = !darkMode
    setDarkMode(newDark)
    document.documentElement.classList.toggle('dark', newDark)
    localStorage.setItem('theme', newDark ? 'dark' : 'light')
  }

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setProfileOpen(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])

  const page: { title: string; crumb?: string } = PAGE_TITLES.find(({ match }) => match(location.pathname)) ?? { title: 'API testing platform' }

  return (
    <header className="sticky top-0 z-30 border-b bg-[var(--app-surface)]">
      <div className="flex h-[68px] items-center justify-between px-4 lg:px-8">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="rounded-lg p-2 text-[var(--app-text-muted)] transition-colors hover:bg-[var(--app-surface-muted)] hover:text-[var(--app-text)] lg:hidden"
            aria-label="Open menu"
          >
            <List className="h-6 w-6" />
          </button>
          <div className="hidden sm:block">
            {page.crumb && <p className="mb-0.5 text-xs text-[var(--app-text-muted)]">{page.crumb} <span className="mx-1 text-[#b5bbc6]">/</span> {page.title}</p>}
            <h1 className="text-base font-semibold leading-tight text-[var(--app-text)]">{page.title}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleDarkMode}
            className="rounded-lg p-2 text-[var(--app-text-muted)] transition-colors hover:bg-[var(--app-surface-muted)] hover:text-[var(--app-text)] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 rounded-lg p-1.5 transition-colors hover:bg-[var(--app-surface-muted)] focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              aria-expanded={profileOpen}
              aria-haspopup="true"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100">
                <User className="h-4 w-4 text-brand-700" />
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-[var(--app-text)]">{user?.full_name || 'User'}</p>
                <p className="text-xs text-[var(--app-text-muted)]">{user?.email}</p>
              </div>
              <CaretDown className="h-4 w-4 text-zinc-400" />
            </button>

            {profileOpen && (
              <div className="app-card absolute right-0 z-50 mt-2 w-52 rounded-xl py-1.5 shadow-lg animate-slide-down">
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-[var(--app-text)] hover:bg-[var(--app-surface-muted)]"
                  onClick={() => setProfileOpen(false)}
                >
                  <Gear className="h-4 w-4" />
                  Settings
                </Link>
                <hr className="my-1" />
                <button
                  onClick={() => {
                    logout()
                    setProfileOpen(false)
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-[#c65c65] hover:bg-[var(--app-surface-muted)]"
                >
                  <SignOut className="h-4 w-4" />
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
