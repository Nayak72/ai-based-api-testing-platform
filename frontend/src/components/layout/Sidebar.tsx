import { Link, useLocation, NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  User,
  SignOut,
  SquaresFour,
  Database,
  PlayCircle,
  FileText,
  Gear,
  CaretLeft,
  RocketLaunch,
  PaperPlaneRight,
  Books,
} from '@phosphor-icons/react'
import { clsx } from 'clsx'
import { Button } from '../ui/Button'

const navigation = [
  { name: 'Dashboard', href: '/', icon: SquaresFour },
  { name: 'New Session', href: '/sessions/new', icon: RocketLaunch },
  { name: 'Quick Test', href: '/quick-test', icon: PaperPlaneRight },
  { name: 'Knowledge Base', href: '/knowledge-base', icon: Books },
  { name: 'Specifications', href: '/specs', icon: Database },
  { name: 'Test Runs', href: '/runs', icon: PlayCircle },
  { name: 'Reports', href: '/reports', icon: FileText },
]

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export function Sidebar({ isOpen, onClose, collapsed = false, onToggleCollapse }: SidebarProps) {
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <>
      <div
        className={clsx(
          'fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-40 bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 transition-all duration-300 flex flex-col h-full',
          collapsed ? 'w-20' : 'w-64',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-zinc-200 dark:border-zinc-800 flex-shrink-0">
          {!collapsed && (
            <Link to="/" className="flex items-center gap-2" aria-label="API Testing Platform">
              <div className="w-8 h-8 rounded-12 bg-brand-600 flex items-center justify-center flex-shrink-0">
                <Database className="h-5 w-5 text-white" />
              </div>
              <span className="font-semibold text-lg text-zinc-900 dark:text-zinc-50 truncate">API Tester</span>
            </Link>
          )}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className={clsx('p-1.5 rounded-8 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors', collapsed && 'mx-auto')}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-expanded={!collapsed}
            >
              {collapsed ? <CaretLeft className="h-5 w-5 rotate-180" /> : <CaretLeft className="h-5 w-5" />}
            </button>
          )}
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" aria-label="Main">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.href || (item.href !== '/' && location.pathname.startsWith(item.href))
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={({ isActive: active }) => clsx(
                  'sidebar-link',
                  active && 'sidebar-link-active',
                  collapsed && 'justify-center px-2'
                )}
                aria-current={isActive ? 'page' : undefined}
                title={collapsed ? item.name : undefined}
              >
                <Icon className="h-5 w-5 flex-shrink-0" aria-hidden="true" />
                {!collapsed && <span>{item.name}</span>}
              </NavLink>
            )
          })}
        </nav>

        <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 flex-shrink-0">
          {!collapsed ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3 px-2 py-1.5">
                <div className="w-8 h-8 rounded-12 bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                  <User className="h-5 w-5 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50 truncate">{user?.full_name || user?.email}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">{user?.email}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Link to="/settings" className="flex-1" onClick={onClose}>
                  <Button variant="ghost" size="sm" className="w-full">
                    <Gear className="h-4 w-4" />
                    <span className="hidden sm:inline">Settings</span>
                  </Button>
                </Link>
                <Button variant="ghost" size="sm" className="flex-1" onClick={() => { logout(); onClose(); }}>
                  <SignOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Logout</span>
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <button
                className="sidebar-link justify-center px-2"
                title="Profile"
                onClick={onClose}
              >
                <User className="h-5 w-5" />
              </button>
              <button
                className="sidebar-link justify-center px-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                title="Logout"
                onClick={() => { logout(); onClose(); }}
              >
                <SignOut className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}