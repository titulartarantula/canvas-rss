import { useMemo } from 'react'

type StatusType = 'beta' | 'preview' | 'optional' | 'released' | 'deprecated' | 'pending' | 'default_on' | 'stable' | string

interface StatusPillProps {
  status: StatusType
  size?: 'sm' | 'md'
  showDot?: boolean
}

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  // lifecycle_stage values for feature_options
  feature_preview: {
    label: 'Preview',
    color: 'text-status-preview',
    bg: 'bg-status-preview/15',
  },
  optional: {
    label: 'Optional',
    color: 'text-status-optional',
    bg: 'bg-status-optional/15',
  },
  // Feature settings statuses (legacy aliases kept for feature_settings display)
  beta: {
    label: 'Beta',
    color: 'text-status-beta',
    bg: 'bg-status-beta/15',
  },
  preview: {
    label: 'Preview',
    color: 'text-status-preview',
    bg: 'bg-status-preview/15',
  },
  default_on: {
    label: 'Default On',
    color: 'text-status-optional',
    bg: 'bg-status-optional/15',
  },
  released: {
    label: 'Released',
    color: 'text-status-released',
    bg: 'bg-status-released/15',
  },
  delayed: {
    label: 'Delayed',
    color: 'text-amber-400',
    bg: 'bg-amber-400/15',
  },
  stable: {
    label: 'Stable',
    color: 'text-status-released',
    bg: 'bg-status-released/15',
  },
  deprecated: {
    label: 'Deprecated',
    color: 'text-status-deprecated',
    bg: 'bg-status-deprecated/15',
  },
  pending: {
    label: 'Pending',
    color: 'text-status-pending',
    bg: 'bg-status-pending/15',
  },
}

export default function StatusPill({ status, size = 'sm', showDot = true }: StatusPillProps) {
  const config = useMemo(() => {
    const normalizedStatus = status?.toLowerCase().replace(/\s+/g, '_') || 'optional'
    return statusConfig[normalizedStatus] || statusConfig.optional
  }, [status])

  const sizeClasses = size === 'sm'
    ? 'px-1.5 py-0.5 text-[11px] gap-1'
    : 'px-2.5 py-0.5 text-xs gap-1.5'

  return (
    <span
      className={`
        inline-flex items-center rounded-md font-mono font-medium uppercase tracking-wider
        ${sizeClasses} ${config.bg} ${config.color}
      `}
    >
      {showDot && (
        <span className={`w-1 h-1 rounded-full bg-current animate-pulse-dot`} />
      )}
      {config.label}
    </span>
  )
}

interface DatePillProps {
  label: string
  date: string | null
  variant?: 'beta' | 'prod'
}

export function DatePill({ label, date, variant = 'beta' }: DatePillProps) {
  if (!date) return null

  const [year, month, day] = date.split('-').map(Number)
  const formattedDate = new Date(year, month - 1, day).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })

  const variantStyles = variant === 'beta'
    ? 'text-status-beta'
    : 'text-status-released'

  return (
    <span className="inline-flex items-center gap-1 font-mono text-xs">
      <span className="text-zinc-400">{label}</span>
      <span className={`font-medium ${variantStyles}`}>{formattedDate}</span>
    </span>
  )
}
