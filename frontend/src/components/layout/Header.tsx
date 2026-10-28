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
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const isDark = saved === 'dark' || (saved !== 'light' && prefersDark)
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
    <header className="glass-surface sticky top-0 z-30 border-x-0 border-t-0">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Open menu"
          >
            <List className="h-6 w-6" />
          </button>
          <div className="hidden sm:block">
            {page.crumb && <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{page.crumb}</p>}
            <h1 className="text-base font-semibold text-slate-950 dark:text-white">{page.title}</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleDarkMode}
            className="rounded-12 p-2 text-slate-500 transition-colors hover:bg-white/70 hover:text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 rounded-12 p-1.5 transition-colors hover:bg-white/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:hover:bg-slate-800"
              aria-expanded={profileOpen}
              aria-haspopup="true"
            >
              <div className="w-8 h-8 rounded-12 bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                <User className="h-5 w-5 text-brand-600 dark:text-brand-400" />
              </div>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{user?.full_name || 'User'}</p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">{user?.email}</p>
              </div>
              <CaretDown className="h-4 w-4 text-zinc-400" />
            </button>

            {profileOpen && (
              <div className="glass-surface absolute right-0 z-50 mt-2 w-52 rounded-16 py-1.5 animate-slide-down">
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  onClick={() => setProfileOpen(false)}
                >
                  <Gear className="h-4 w-4" />
                  Settings
                </Link>
                <hr className="my-1 border-zinc-200 dark:border-zinc-800" />
                <button
                  onClick={() => {
                    logout()
                    setProfileOpen(false)
                  }}
                  className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-left"
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
