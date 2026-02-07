import { Link } from 'react-router-dom'
import type { Release } from '../types'
import { DocumentIcon, ArrowRightIcon } from './icons'

interface ReleaseRowProps {
  release: Release
  index?: number
}

export default function ReleaseRow({ release, index = 0 }: ReleaseRowProps) {
  const isDeployNote = release.content_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy' : 'Release'
  const typeColor = isDeployNote ? 'text-status-optional bg-status-optional/10' : 'text-status-beta bg-status-beta/10'

  const dateStr = release.first_posted || release.published_date || ''
  // Parse date portion directly to avoid timezone shift
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const date = match
    ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
    : new Date(dateStr)
  const formattedDate = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })

  return (
    <Link
      to={`/releases/${release.source_id}`}
      className="
        group flex items-center gap-4 py-4 px-4 -mx-4 rounded-lg
        hover:bg-ink-50 transition-colors
        animate-slide-up
      "
      style={{ animationDelay: `${index * 25}ms` }}
    >
      {/* Date column */}
      <div className="w-16 flex-shrink-0 text-center">
        <span className="text-sm font-medium text-ink-700">{formattedDate}</span>
      </div>

      {/* Type badge */}
      <div className="w-20 flex-shrink-0">
        <span className={`
          inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide
          ${typeColor}
        `}>
          {typeLabel}
        </span>
      </div>

      {/* Title and summary */}
      <div className="flex-1 min-w-0">
        <h4 className="font-medium text-ink-900 group-hover:text-accent-primary transition-colors truncate">
          {release.title}
        </h4>
        {release.summary && (
          <p className="mt-0.5 text-sm text-ink-500 truncate">
            {release.summary}
          </p>
        )}
      </div>

      {/* Announcement count */}
      {release.announcement_count !== undefined && release.announcement_count > 0 && (
        <div className="flex-shrink-0 flex items-center gap-1.5 text-xs text-ink-500">
          <DocumentIcon className="w-3.5 h-3.5" />
          <span>
            {release.announcement_count} {release.announcement_count === 1 ? 'announcement' : 'announcements'}
          </span>
        </div>
      )}

      {/* Arrow */}
      <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <ArrowRightIcon className="w-4 h-4 text-ink-400" />
      </div>
    </Link>
  )
}

// Skeleton for loading state
export function ReleaseRowSkeleton() {
  return (
    <div className="flex items-center gap-4 py-4 px-4 -mx-4">
      <div className="w-16 flex-shrink-0">
        <div className="skeleton h-4 w-12 mx-auto" />
      </div>
      <div className="w-20 flex-shrink-0">
        <div className="skeleton h-5 w-16 rounded" />
      </div>
      <div className="flex-1">
        <div className="skeleton h-5 w-64" />
        <div className="mt-1 skeleton h-4 w-48" />
      </div>
      <div className="flex-shrink-0">
        <div className="skeleton h-4 w-24" />
      </div>
    </div>
  )
}
