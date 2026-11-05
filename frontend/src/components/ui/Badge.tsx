import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'warning' | 'error' | 'info' | 'gray' | 'default'
  size?: 'sm' | 'md'
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    const variants = {
      success: 'bg-[var(--app-success-soft)] text-[#25876b]',
      warning: 'bg-[var(--app-warning-soft)] text-[#b98232]',
      error: 'bg-[var(--app-error-soft)] text-[#c65c65]',
      info: 'bg-[var(--app-accent-soft)] text-brand-700 dark:text-brand-300',
      gray: 'bg-[var(--app-surface-muted)] text-[var(--app-text-muted)]',
      default: 'bg-[var(--app-accent-soft)] text-brand-700 dark:text-brand-300',
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
