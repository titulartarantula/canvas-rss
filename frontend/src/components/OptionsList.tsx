import { Link } from 'react-router-dom'
import type { FeatureOption } from '../types'
import StatusPill, { DatePill } from './StatusPill'
import { ArrowRightIcon } from './icons'

interface OptionsListProps {
  options: FeatureOption[]
  emptyMessage?: string
}

export default function OptionsList({ options, emptyMessage = 'No feature options' }: OptionsListProps) {
  if (options.length === 0) {
    return (
      <div className="text-center py-8 text-ink-500 text-sm">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="divide-y divide-ink-100">
      {options.map((option, index) => (
        <OptionRow key={option.option_id} option={option} index={index} />
      ))}
    </div>
  )
}

function OptionRow({ option, index }: { option: FeatureOption; index: number }) {
  return (
    <Link
      to={`/options/${option.option_id}`}
      className="group flex items-start gap-4 py-4 px-2 -mx-2 rounded-lg hover:bg-ink-50 transition-colors"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 flex-wrap">
          <h4 className="font-medium text-ink-900 group-hover:text-accent-primary transition-colors">
            {option.canonical_name || option.name}
          </h4>
          <StatusPill status={option.status} size="sm" />
        </div>

        {/* Description */}
        {option.description && (
          <p className="mt-1.5 text-sm text-ink-600 line-clamp-2 leading-relaxed">
            {option.description}
          </p>
        )}

        {/* Lifecycle dates */}
        <div className="mt-2 flex items-center gap-4">
          <DatePill label="Beta" date={option.beta_date} variant="beta" />
          <DatePill label="Prod" date={option.production_date} variant="prod" />
          {option.deprecation_date && (
            <span className="text-xs text-status-deprecated">
              Deprecated {(() => { const m = option.deprecation_date.match(/^(\d{4})-(\d{2})-(\d{2})/); const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(option.deprecation_date); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); })()}
            </span>
          )}
        </div>
      </div>

      {/* Arrow indicator */}
      <div className="flex-shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <ArrowRightIcon className="w-4 h-4 text-ink-400" />
      </div>
    </Link>
  )
}

// Skeleton for loading state
export function OptionsListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="divide-y divide-ink-100">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="py-4">
          <div className="flex items-center gap-3">
            <div className="skeleton h-5 w-48" />
            <div className="skeleton h-5 w-16 rounded-full" />
          </div>
          <div className="mt-2 skeleton h-4 w-full max-w-md" />
          <div className="mt-2 flex gap-4">
            <div className="skeleton h-4 w-20" />
            <div className="skeleton h-4 w-20" />
          </div>
        </div>
      ))}
    </div>
  )
}
