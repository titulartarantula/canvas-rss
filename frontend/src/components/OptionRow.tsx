import { Link } from 'react-router-dom'
import type { FeatureOption } from '../types'
import StatusPill, { DatePill } from './StatusPill'
import { ArrowRightIcon } from './icons'

interface OptionRowProps {
  option: FeatureOption
  index?: number
}

export default function OptionRow({ option, index = 0 }: OptionRowProps) {
  const displayName = option.canonical_name || option.name

  return (
    <Link
      to={`/options/${option.option_id}`}
      className="
        group block card p-5
        hover:shadow-card-hover hover:border-ink-200
        transition-all duration-200
        animate-slide-up
      "
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Top row: name and status */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h3 className="font-display text-base font-semibold text-ink-900 group-hover:text-accent-primary transition-colors">
              {displayName}
            </h3>
            <StatusPill status={option.status} size="sm" />
          </div>

          {/* Feature name */}
          {option.feature_name && (
            <p className="mt-1 text-xs text-ink-500">
              in <span className="font-medium text-ink-600">{option.feature_name}</span>
            </p>
          )}
        </div>

        {/* Arrow indicator */}
        <div className="flex-shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <ArrowRightIcon className="w-4 h-4 text-ink-400" />
        </div>
      </div>

      {/* Description */}
      {(option.description || option.meta_summary) && (
        <p className="mt-3 text-sm text-ink-600 leading-relaxed line-clamp-2">
          {option.description || option.meta_summary}
        </p>
      )}

      {/* Footer with dates and config */}
      <div className="mt-4 pt-3 border-t border-ink-100 flex flex-wrap items-center gap-x-5 gap-y-2">
        <DatePill label="Beta" date={option.beta_date} variant="beta" />
        <DatePill label="Prod" date={option.production_date} variant="prod" />

        {option.deprecation_date && (
          <span className="text-xs text-status-deprecated flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-status-deprecated" />
            Deprecated {(() => { const m = option.deprecation_date.match(/^(\d{4})-(\d{2})-(\d{2})/); const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(option.deprecation_date); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); })()}
          </span>
        )}

        {option.config_level && (
          <span className="text-xs text-ink-500">
            {option.config_level}
          </span>
        )}
      </div>
    </Link>
  )
}

// Skeleton for loading state
export function OptionRowSkeleton() {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <div className="skeleton h-5 w-48" />
            <div className="skeleton h-5 w-16 rounded-full" />
          </div>
          <div className="mt-1 skeleton h-3 w-24" />
        </div>
      </div>
      <div className="mt-3 space-y-2">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
      <div className="mt-4 pt-3 border-t border-ink-100 flex gap-5">
        <div className="skeleton h-4 w-20" />
        <div className="skeleton h-4 w-20" />
      </div>
    </div>
  )
}
