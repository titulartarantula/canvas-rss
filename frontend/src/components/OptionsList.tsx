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
    return <div className="text-center py-6 text-xs text-zinc-500 font-mono">{emptyMessage}</div>
  }

  return (
    <div className="card overflow-hidden">
      {options.map((option) => (
        <Link
          key={option.option_id}
          to={`/options/${option.option_id}`}
          className="data-row group"
        >
          <div className="flex-shrink-0 flex items-center gap-1">
            <StatusPill status={option.lifecycle_stage} size="sm" showDot={false} />
            {option.will_be_enforced && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/15 text-amber-400">Enforced</span>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
              {option.canonical_name || option.name}
            </span>
            {option.description && (
              <p className="mt-0.5 text-xs text-zinc-500 truncate">{option.description}</p>
            )}
          </div>
          <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
            <DatePill label="B" date={option.beta_date} variant="beta" />
            <DatePill label="P" date={option.production_date} variant="prod" />
          </div>
          <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
        </Link>
      ))}
    </div>
  )
}

export function OptionsListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="card overflow-hidden">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="data-row">
          <div className="w-20"><div className="skeleton h-4 w-14 rounded" /></div>
          <div className="flex-1"><div className="skeleton h-4 w-48" /></div>
        </div>
      ))}
    </div>
  )
}
