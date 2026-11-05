import { ReactNode } from 'react'
import { ArrowClockwise, Info, WarningCircle } from '@phosphor-icons/react'
import { Button } from './Button'

interface StatePanelProps {
  title: string
  description: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState({ title, description, action, icon }: StatePanelProps) {
  return (
    <div className="state-panel">
      {icon ?? <Info className="mb-3 h-8 w-8 text-slate-400" aria-hidden="true" />}
      <h3 className="text-base font-semibold text-[var(--app-text)]">{title}</h3>
      <p className="mt-1 max-w-md text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ title = 'Unable to load this data', description, onRetry }: {
  title?: string
  description: string
  onRetry?: () => void
}) {
  return (
    <div className="state-panel border-[#e9c2c6] bg-[var(--app-error-soft)]" role="alert">
      <WarningCircle className="mb-3 h-8 w-8 text-red-600 dark:text-red-400" aria-hidden="true" />
      <h3 className="text-base font-semibold text-[var(--app-text)]">{title}</h3>
      <p className="mt-1 max-w-md text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
      {onRetry && (
        <Button className="mt-4" variant="secondary" size="sm" onClick={onRetry}>
          <ArrowClockwise className="h-4 w-4" /> Retry
        </Button>
      )}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-[#e9ecf1] dark:bg-[#394150] ${className}`} aria-hidden="true" />
}
