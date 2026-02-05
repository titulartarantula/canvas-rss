import { Link } from 'react-router-dom'
import type { Feature } from '../types'

interface FeatureCardProps {
  feature: Feature
  index?: number
}

export default function FeatureCard({ feature, index = 0 }: FeatureCardProps) {
  const optionCount = feature.option_count || 0
  const statusSummary = feature.status_summary || ''

  return (
    <Link
      to={`/features/${feature.feature_id}`}
      className="group card p-5 flex flex-col h-full hover:shadow-card-hover transition-all duration-200"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Header with name */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-display text-base font-semibold text-ink-900 group-hover:text-accent-primary transition-colors leading-snug">
          {feature.name}
        </h3>
        {optionCount > 0 && (
          <span className="flex-shrink-0 px-2 py-0.5 text-xs font-medium bg-ink-100 text-ink-600 rounded-full">
            {optionCount}
          </span>
        )}
      </div>

      {/* Description */}
      {feature.description && (
        <p className="mt-2 text-sm text-ink-600 leading-relaxed line-clamp-2 flex-1">
          {feature.description}
        </p>
      )}

      {/* Status summary footer */}
      <div className="mt-4 pt-3 border-t border-ink-100">
        {statusSummary ? (
          <StatusSummary summary={statusSummary} />
        ) : optionCount === 0 ? (
          <span className="text-xs text-ink-400">No feature options</span>
        ) : (
          <span className="text-xs text-status-released flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-status-released" />
            All stable
          </span>
        )}
      </div>
    </Link>
  )
}

function StatusSummary({ summary }: { summary: string }) {
  // Parse the summary string like "2 in preview, 1 pending"
  const parts = summary.split(',').map(s => s.trim())

  return (
    <div className="flex flex-wrap items-center gap-2">
      {parts.map((part, idx) => {
        const color = getStatusColor(part)
        return (
          <span
            key={idx}
            className={`text-xs flex items-center gap-1.5 ${color}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${getStatusDotColor(part)}`} />
            {part}
          </span>
        )
      })}
    </div>
  )
}

function getStatusColor(text: string): string {
  if (text.includes('preview')) return 'text-status-preview'
  if (text.includes('pending')) return 'text-status-pending'
  if (text.includes('optional')) return 'text-status-optional'
  if (text.includes('beta')) return 'text-status-beta'
  if (text.includes('stable') || text.includes('released')) return 'text-status-released'
  return 'text-ink-600'
}

function getStatusDotColor(text: string): string {
  if (text.includes('preview')) return 'bg-status-preview'
  if (text.includes('pending')) return 'bg-status-pending'
  if (text.includes('optional')) return 'bg-status-optional'
  if (text.includes('beta')) return 'bg-status-beta'
  if (text.includes('stable') || text.includes('released')) return 'bg-status-released'
  return 'bg-ink-400'
}

// Skeleton loader for feature cards
export function FeatureCardSkeleton() {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div className="skeleton h-5 w-32" />
        <div className="skeleton h-5 w-8 rounded-full" />
      </div>
      <div className="mt-3 space-y-2">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
      <div className="mt-4 pt-3 border-t border-ink-100">
        <div className="skeleton h-3 w-24" />
      </div>
    </div>
  )
}
