import { Outlet } from 'react-router-dom'
import { useState, ReactNode } from 'react'
import { Header } from './Header'
import { Sidebar } from './Sidebar'
import { clsx } from 'clsx'

interface LayoutProps {
  children?: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
      />
      <div className={clsx('flex flex-col min-h-screen transition-all duration-300', collapsed ? 'lg:pl-20' : 'lg:pl-64')}>
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-4 lg:p-6">
          {children || <Outlet />}
        </main>
      </div>
    </div>
  )
}