import { Link } from 'react-router-dom'
import { clsx } from 'clsx'

interface BrandLogoProps {
  compact?: boolean
  className?: string
}

export function BrandLogo({ compact = false, className }: BrandLogoProps) {
  return (
    <Link to="/" className={clsx('flex min-w-0 items-center gap-2.5', compact && 'justify-center', className)} aria-label="API Testing Platform home">
      <img className={clsx('shrink-0', compact ? 'h-12 w-12' : 'h-9 w-9')} src="/brand/api-platform-mark.svg" alt="" />
      {!compact && <span className="min-w-0"><span className="block truncate text-sm font-semibold tracking-[-.01em] text-white">API Testing Platform</span><span className="block font-mono text-[9px] uppercase tracking-[.11em] text-[#98a1b1]">Engineering workspace</span></span>}
    </Link>
  )
}
