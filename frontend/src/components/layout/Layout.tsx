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
    <div className="app-shell overflow-x-hidden">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
      />
      <div className={clsx('flex min-h-screen flex-col transition-all duration-300', collapsed ? 'lg:pl-20' : 'lg:pl-[248px]')}>
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-7">
          {children || <Outlet />}
        </main>
      </div>
    </div>
  )
}
