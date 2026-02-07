import type { UpcomingChange } from '../types'
import { ExclamationTriangleIcon, CalendarIcon } from './icons'

interface UpcomingChangesProps {
  changes: UpcomingChange[]
  isLoading?: boolean
}

export default function UpcomingChanges({ changes, isLoading }: UpcomingChangesProps) {
  if (isLoading) {
    return (
      <div className="card p-6 h-full">
        <Header />
        <div className="mt-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <div className="skeleton w-16 h-4" />
              <div className="skeleton flex-1 h-4" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (changes.length === 0) {
    return (
      <div className="card p-6 h-full">
        <Header />
        <div className="mt-6 text-center py-8">
          <CalendarIcon className="w-8 h-8 mx-auto text-ink-300" />
          <p className="mt-3 text-sm text-ink-500">No upcoming changes</p>
        </div>
      </div>
    )
  }

  // Group changes by urgency
  const now = new Date()
  const parseLocalDate = (dateStr: string): Date => {
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
    return match
      ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
      : new Date(dateStr)
  }
  const sortedChanges = [...changes].sort(
    (a, b) => parseLocalDate(a.change_date).getTime() - parseLocalDate(b.change_date).getTime()
  )

  return (
    <div className="card p-6 h-full flex flex-col">
      <Header count={changes.length} />

      <div className="mt-5 flex-1 space-y-1">
        {sortedChanges.map((change, idx) => (
          <ChangeItem key={idx} change={change} now={now} />
        ))}
      </div>
    </div>
  )
}

function Header({ count }: { count?: number }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <h3 className="font-display text-lg font-semibold text-ink-900">Upcoming Changes</h3>
        {count !== undefined && count > 0 && (
          <span className="px-2 py-0.5 text-xs font-medium bg-status-deprecated/10 text-status-deprecated rounded-full">
            {count}
          </span>
        )}
      </div>
    </div>
  )
}

function ChangeItem({ change, now }: { change: UpcomingChange; now: Date }) {
  const cdStr = change.change_date || ''
  const cdMatch = cdStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const changeDate = cdMatch
    ? new Date(Number(cdMatch[1]), Number(cdMatch[2]) - 1, Number(cdMatch[3]))
    : new Date(cdStr)
  const daysUntil = Math.ceil((changeDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

  // Urgency levels
  const isUrgent = daysUntil <= 7
  const isWarning = daysUntil <= 30
  const isPast = daysUntil < 0

  const urgencyClasses = isPast
    ? 'border-l-ink-400 bg-ink-50'
    : isUrgent
    ? 'border-l-status-deprecated bg-status-deprecated/5'
    : isWarning
    ? 'border-l-status-deprecated/50 bg-status-deprecated/5'
    : 'border-l-ink-200 bg-white'

  const dateClasses = isPast
    ? 'text-ink-500'
    : isUrgent
    ? 'text-status-deprecated font-semibold'
    : isWarning
    ? 'text-status-deprecated'
    : 'text-ink-600'

  return (
    <div
      className={`
        relative pl-4 py-3 border-l-2 rounded-r-lg
        transition-colors duration-150 hover:bg-ink-50
        ${urgencyClasses}
      `}
    >
      <div className="flex items-start gap-3">
        {isUrgent && !isPast && (
          <ExclamationTriangleIcon className="w-4 h-4 text-status-deprecated flex-shrink-0 mt-0.5" />
        )}
        <div className="flex-1 min-w-0">
          <div className={`text-xs font-mono ${dateClasses}`}>
            {formatChangeDate(changeDate)}
            {!isPast && (
              <span className="ml-2 text-ink-400">
                ({daysUntil === 0 ? 'Today' : daysUntil === 1 ? 'Tomorrow' : `${daysUntil} days`})
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink-700 leading-snug">
            {change.description}
          </p>
        </div>
      </div>
    </div>
  )
}

function formatChangeDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}
