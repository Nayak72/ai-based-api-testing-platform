import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import {
  List,
  Bell,
  Moon,
  Sun,
  CaretDown,
  User,
  SignOut,
  Gear,
  CheckCircle,
  WarningCircle,
  FileText,
  Sparkle,
  Trash,
  Check,
} from '@phosphor-icons/react'
import { useState, useRef, useEffect } from 'react'
import { clsx } from 'clsx'

interface NotificationItem {
  id: string
  title: string
  message: string
  type: 'success' | 'warning' | 'info' | 'error'
  link?: string
  timestamp: string
  read: boolean
}

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: '1',
    title: 'Platform Initialized',
    message: 'API Testing Platform is ready for spec uploads and AI test generation.',
    type: 'info',
    link: '/specs/upload',
    timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    read: false,
  },
  {
    id: '2',
    title: 'AI Models Connected',
    message: 'OpenRouter and NVIDIA NIM providers configured for deep security scans.',
    type: 'success',
    link: '/settings',
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    read: false,
  },
  {
    id: '3',
    title: 'Compliance Reports Enabled',
    message: 'HTML & PDF export ready for automated test suites.',
    type: 'info',
    link: '/reports',
    timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    read: true,
  },
]

export function Header({ onMenuClick }: { onMenuClick: () => void }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [darkMode, setDarkMode] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>(() => {
    const saved = localStorage.getItem('user_notifications')
    return saved ? JSON.parse(saved) : DEFAULT_NOTIFICATIONS
  })

  const profileRef = useRef<HTMLDivElement>(null)
  const notificationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const isDark = document.documentElement.classList.contains('dark')
    setDarkMode(isDark)
  }, [])

  useEffect(() => {
    localStorage.setItem('user_notifications', JSON.stringify(notifications))
  }, [notifications])

  const toggleDarkMode = () => {
    const newDark = !darkMode
    setDarkMode(newDark)
    document.documentElement.classList.toggle('dark', newDark)
    localStorage.setItem('darkMode', String(newDark))
  }

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(event.target as Node)) {
        setProfileOpen(false)
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }

  const clearAllNotifications = () => {
    setNotifications([])
  }

  const handleNotificationClick = (item: NotificationItem) => {
    markAsRead(item.id)
    setNotificationsOpen(false)
    if (item.link) {
      navigate(item.link)
    }
  }

  const getPageTitle = () => {
    const path = location.pathname
    if (path === '/') return 'Dashboard'
    if (path.startsWith('/specs')) return 'Specifications'
    if (path.startsWith('/runs')) return 'Test Runs'
    if (path.startsWith('/reports')) return 'Reports'
    if (path.startsWith('/settings')) return 'Settings'
    return 'API Testing Platform'
  }

  const getNotificationIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
      case 'warning':
      case 'error':
        return <WarningCircle className="h-5 w-5 text-amber-500 flex-shrink-0" />
      default:
        return <Sparkle className="h-5 w-5 text-brand-500 flex-shrink-0" />
    }
  }

  return (
    <header className="sticky top-0 z-30 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800">
      <div className="flex items-center justify-between h-16 px-4 lg:px-6">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label="Open menu"
          >
            <List className="h-6 w-6" />
          </button>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 hidden sm:block">
            {getPageTitle()}
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Dark Mode Toggle */}
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>

          {/* Notifications Dropdown */}
          <div className="relative" ref={notificationRef}>
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative p-2 rounded-10 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              aria-label="Notifications"
              aria-expanded={notificationsOpen}
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-brand-600 text-[10px] font-bold text-white shadow-sm">
                  {unreadCount}
                </span>
              )}
            </button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-zinc-900 rounded-16 shadow-xl border border-zinc-200 dark:border-zinc-800 py-2 z-50 animate-slide-down">
                <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-100 dark:border-zinc-800">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllAsRead}
                      className="text-xs text-brand-600 hover:text-brand-700 dark:text-brand-400 flex items-center gap-1 font-medium"
                    >
                      <Check className="h-3.5 w-3.5" />
                      Mark all as read
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800/50">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-zinc-400 dark:text-zinc-500 text-sm">
                      <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>You're all caught up!</p>
                      <p className="text-xs text-zinc-400 mt-1">No new notifications</p>
                    </div>
                  ) : (
                    notifications.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => handleNotificationClick(item)}
                        className={clsx(
                          'p-3.5 flex items-start gap-3 hover:bg-zinc-50 dark:hover:bg-zinc-800/60 cursor-pointer transition-colors relative',
                          !item.read && 'bg-brand-50/40 dark:bg-brand-950/20'
                        )}
                      >
                        {getNotificationIcon(item.type)}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-1 mb-0.5">
                            <p className={clsx('text-xs font-medium truncate', !item.read ? 'text-zinc-900 dark:text-zinc-100 font-semibold' : 'text-zinc-700 dark:text-zinc-300')}>
                              {item.title}
                            </p>
                            {!item.read && (
                              <span className="w-2 h-2 rounded-full bg-brand-600 flex-shrink-0" />
                            )}
                          </div>
                          <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                            {item.message}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                {notifications.length > 0 && (
                  <div className="px-4 py-2 border-t border-zinc-100 dark:border-zinc-800 flex justify-between items-center text-xs">
                    <button
                      onClick={clearAllNotifications}
                      className="text-zinc-400 hover:text-red-500 dark:hover:text-red-400 flex items-center gap-1 transition-colors"
                    >
                      <Trash className="h-3.5 w-3.5" />
                      Clear all
                    </button>
                    <Link
                      to="/settings"
                      onClick={() => setNotificationsOpen(false)}
                      className="text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                    >
                      Preferences
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* User Profile Dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 p-1.5 rounded-10 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
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
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-zinc-900 rounded-12 shadow-lg border border-zinc-200 dark:border-zinc-800 py-1 animate-slide-down z-50">
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