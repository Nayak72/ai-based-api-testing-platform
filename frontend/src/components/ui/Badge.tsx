import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'gray' | 'default'
  size?: 'sm' | 'md'
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    const variants = {
      success: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      gray: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300',
      default: 'bg-brand-100 text-brand-800 dark:bg-brand-900/30 dark:text-brand-400',
    }

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-0.5 text-xs',
    }

    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center rounded-full font-medium',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'

export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, BadgeProps['variant']> = {
    passed: 'success',
    failed: 'error',
    error: 'warning',
    skipped: 'gray',
    pending: 'info',
    running: 'info',
    completed: 'success',
    completed_with_errors: 'warning',
    waiting_approval: 'warning',
    cancelled: 'gray',
    cancelling: 'warning',
  }

  const labels: Record<string, string> = {
    passed: 'Passed',
    failed: 'Failed',
    error: 'Error',
    skipped: 'Skipped',
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    completed_with_errors: 'Completed with errors',
    waiting_approval: 'Awaiting approval',
    cancelled: 'Cancelled',
    cancelling: 'Cancelling',
  }

  return (
    <Badge variant={variants[status] || 'default'}>
      {labels[status] || status}
    </Badge>
  )
}

export function SeverityBadge({ severity }: { severity: string }) {
  const variants: Record<string, BadgeProps['variant']> = {
    low: 'success',
    medium: 'warning',
    high: 'error',
    critical: 'error',
  }

  return (
    <Badge variant={variants[severity] || 'default'} size="sm">
      {severity}
    </Badge>
  )
}
