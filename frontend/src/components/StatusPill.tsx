import { useMemo } from 'react'

type StatusType = 'beta' | 'preview' | 'optional' | 'released' | 'deprecated' | 'pending' | 'default_on' | string

interface StatusPillProps {
  status: StatusType
  size?: 'sm' | 'md'
  showDot?: boolean
}

const statusConfig: Record<string, { label: string; dotColor: string; bgColor: string; textColor: string }> = {
  beta: {
    label: 'Beta',
    dotColor: 'bg-status-beta',
    bgColor: 'bg-status-beta/10',
    textColor: 'text-status-beta',
  },
  preview: {
    label: 'Preview',
    dotColor: 'bg-status-preview',
    bgColor: 'bg-status-preview/10',
    textColor: 'text-status-preview',
  },
  optional: {
    label: 'Optional',
    dotColor: 'bg-status-optional',
    bgColor: 'bg-status-optional/10',
    textColor: 'text-status-optional',
  },
  default_on: {
    label: 'Default On',
    dotColor: 'bg-status-optional',
    bgColor: 'bg-status-optional/10',
    textColor: 'text-status-optional',
  },
  released: {
    label: 'Released',
    dotColor: 'bg-status-released',
    bgColor: 'bg-status-released/10',
    textColor: 'text-status-released',
  },
  deprecated: {
    label: 'Deprecated',
    dotColor: 'bg-status-deprecated',
    bgColor: 'bg-status-deprecated/10',
    textColor: 'text-status-deprecated',
  },
  pending: {
    label: 'Pending',
    dotColor: 'bg-status-pending',
    bgColor: 'bg-status-pending/10',
    textColor: 'text-status-pending',
  },
}

export default function StatusPill({ status, size = 'sm', showDot = true }: StatusPillProps) {
  const config = useMemo(() => {
    const normalizedStatus = status?.toLowerCase().replace(/\s+/g, '_') || 'pending'
    return statusConfig[normalizedStatus] || statusConfig.pending
  }, [status])

  const sizeClasses = size === 'sm'
    ? 'px-2 py-0.5 text-[10px]'
    : 'px-2.5 py-1 text-xs'

  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium tracking-wide uppercase
        ${sizeClasses} ${config.bgColor} ${config.textColor}
        transition-colors duration-150
      `}
    >
      {showDot && (
        <span className={`${dotSize} rounded-full ${config.dotColor} animate-pulse-soft`} />
      )}
      {config.label}
    </span>
  )
}

// Date-based status pills for lifecycle dates
interface DatePillProps {
  label: string
  date: string | null
  variant?: 'beta' | 'prod'
}

export function DatePill({ label, date, variant = 'beta' }: DatePillProps) {
  if (!date) return null

  // Parse date parts directly to avoid timezone shift
  // (new Date('2026-01-19') is midnight UTC, shifts back a day in local tz)
  const [year, month, day] = date.split('-').map(Number)
  const formattedDate = new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })

  const variantStyles = variant === 'beta'
    ? 'text-status-beta'
    : 'text-status-released'

  return (
    <span className={`inline-flex items-center gap-1 text-xs ${variantStyles}`}>
      <span className="text-ink-500 font-normal">{label}</span>
      <span className="font-medium">{formattedDate}</span>
    </span>
  )
}
