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
import { BrandLogo } from '../brand/BrandLogo'

const navigation = [
  { label: 'Workspace', items: [
    { name: 'Overview', href: '/', icon: SquaresFour },
    { name: 'New Session', href: '/sessions/new', icon: RocketLaunch },
    { name: 'Quick Test', href: '/quick-test', icon: PaperPlaneRight },
  ] },
  { label: 'API Assets', items: [
    { name: 'Specifications', href: '/specs', icon: Database },
    { name: 'Knowledge Base', href: '/knowledge-base', icon: Books },
  ] },
  { label: 'Results', items: [
    { name: 'Test Runs', href: '/runs', icon: PlayCircle },
    { name: 'Reports', href: '/reports', icon: FileText },
  ] },
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
          'fixed inset-y-0 left-0 z-40 flex h-full flex-col border-y-0 border-l-0 border-r border-[#272e3b] bg-[#171c26] transition-all duration-300',
          collapsed ? 'w-20' : 'w-[248px]',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
        aria-label="Main navigation"
      >
        <div className={clsx('relative flex h-[68px] flex-shrink-0 items-center border-b border-[#272e3b]', collapsed ? 'justify-center px-2' : 'justify-between px-4')}>
          <BrandLogo compact={collapsed} />
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className={clsx('rounded-lg p-1.5 text-[#98a1b1] transition-colors hover:bg-white/5 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400', collapsed && 'absolute right-1.5')}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              aria-expanded={!collapsed}
            >
              {collapsed ? <CaretLeft className="h-5 w-5 rotate-180" /> : <CaretLeft className="h-5 w-5" />}
            </button>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-3" aria-label="Main">
          {navigation.map((group) => <div key={group.label} className="mb-1">
            {!collapsed && <p className="sidebar-section">{group.label}</p>}
            {collapsed && <div className="mx-2 my-3 h-px bg-white/10" />}
            {group.items.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href || (item.href !== '/' && location.pathname.startsWith(item.href))
              return <NavLink key={item.name} to={item.href} onClick={onClose} className={({ isActive: active }) => clsx('sidebar-link', active && 'sidebar-link-active', collapsed && 'justify-center px-2')} aria-current={isActive ? 'page' : undefined} title={collapsed ? item.name : undefined}>
                <Icon className="h-[18px] w-[18px] flex-shrink-0" aria-hidden="true" />
                {!collapsed && <span>{item.name}</span>}
              </NavLink>
            })}
          </div>)}
        </nav>

        <div className="flex-shrink-0 border-t border-[#272e3b] p-3">
          {!collapsed ? (
            <div className="space-y-2">
              <div className="flex items-center gap-3 px-2 py-1.5">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#30394a]">
                  <User className="h-4 w-4 text-[#c7cedb]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-[#f4f5f7]">{user?.full_name || user?.email}</p>
                  <p className="truncate text-xs text-[#98a1b1]">{user?.email}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Link to="/settings" className="flex-1" onClick={onClose}>
                  <Button variant="ghost" size="sm" className="w-full !text-[#c0c7d3] hover:!bg-white/5 hover:!text-white">
                    <Gear className="h-4 w-4" />
                    <span className="hidden sm:inline">Settings</span>
                  </Button>
                </Link>
                <Button variant="ghost" size="sm" className="flex-1 !text-[#c0c7d3] hover:!bg-white/5 hover:!text-white" onClick={() => { logout(); onClose(); }}>
                  <SignOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Logout</span>
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Link
                to="/settings"
                aria-label="Settings"
                className="sidebar-link justify-center px-2"
                title="Profile"
                onClick={onClose}
              >
                <User className="h-5 w-5" />
              </Link>
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
