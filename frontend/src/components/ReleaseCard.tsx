import { Link } from 'react-router-dom'
import type { Release, Announcement } from '../types'
import StatusPill, { DatePill } from './StatusPill'
import { ArrowRightIcon, ArchiveIcon, ExternalLinkIcon } from './icons'

interface ReleaseCardProps {
  release: Release | null
  type: 'release' | 'deploy'
  isLoading?: boolean
}

export default function ReleaseCard({ release, type, isLoading }: ReleaseCardProps) {
  const title = type === 'release' ? 'Release Notes' : 'Deploy Notes'
  const emptyMessage = type === 'release'
    ? 'No release notes for this period'
    : 'No deploy notes for this period'

  if (isLoading) {
    return (
      <div className="card p-6 h-full">
        <CardHeader title={title} />
        <div className="mt-4 space-y-3">
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-5/6" />
        </div>
      </div>
    )
  }

  if (!release) {
    return (
      <div className="card p-6 h-full">
        <CardHeader title={title} />
        <div className="mt-6 text-center py-8">
          <p className="text-ink-500 text-sm">{emptyMessage}</p>
        </div>
      </div>
    )
  }

  const announcements = release.announcements || []
  const displayCount = 5
  const hasMore = announcements.length > displayCount

  return (
    <div className="card p-6 h-full flex flex-col">
      <CardHeader
        title={title}
        subtitle={formatPublishDate(release.first_posted || release.published_date)}
        url={release.url}
      />

      {/* Summary */}
      {release.summary && (
        <p className="mt-4 text-sm text-ink-600 leading-relaxed line-clamp-3">
          {release.summary}
        </p>
      )}

      {/* Feature announcements */}
      {announcements.length > 0 && (
        <div className="mt-5 flex-1">
          <div className="space-y-3">
            {announcements.slice(0, displayCount).map((announcement, idx) => (
              <AnnouncementItem key={announcement.id || idx} announcement={announcement} />
            ))}
          </div>
          {hasMore && (
            <p className="mt-3 text-xs text-ink-500">
              +{announcements.length - displayCount} more features
            </p>
          )}
        </div>
      )}

      {/* Footer actions */}
      <div className="mt-6 pt-4 border-t border-ink-100 flex items-center justify-between">
        <Link
          to={`/releases/${release.source_id}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent-primary hover:text-accent-primary/80 transition-colors"
        >
          View full
          <ArrowRightIcon className="w-3.5 h-3.5" />
        </Link>
        <Link
          to="/releases"
          className="inline-flex items-center gap-1.5 text-sm text-ink-500 hover:text-ink-700 transition-colors"
        >
          <ArchiveIcon className="w-4 h-4" />
          Browse archive
        </Link>
      </div>
    </div>
  )
}

function CardHeader({
  title,
  subtitle,
  url,
}: {
  title: string
  subtitle?: string
  url?: string
}) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h3 className="font-display text-lg font-semibold text-ink-900">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-ink-500 font-mono">{subtitle}</p>
        )}
      </div>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1.5 text-ink-400 hover:text-ink-600 hover:bg-ink-100 rounded transition-colors"
          title="View original"
        >
          <ExternalLinkIcon className="w-4 h-4" />
        </a>
      )}
    </div>
  )
}

function AnnouncementItem({ announcement }: { announcement: Announcement }) {
  const optionLink = announcement.option_id
    ? `/options/${announcement.option_id}`
    : null

  return (
    <div className="group">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {optionLink ? (
            <Link
              to={optionLink}
              className="text-sm font-medium text-ink-800 hover:text-accent-primary transition-colors line-clamp-1"
            >
              {announcement.h4_title}
            </Link>
          ) : (
            <span className="text-sm font-medium text-ink-800 line-clamp-1">
              {announcement.h4_title}
            </span>
          )}

          {/* Description */}
          {announcement.description && (
            <p className="mt-1 text-xs text-ink-500 leading-relaxed line-clamp-2">
              {announcement.description}
            </p>
          )}

          {/* Lifecycle dates */}
          <div className="mt-1 flex items-center gap-3">
            {announcement.option_status && (
              <StatusPill status={announcement.option_status} size="sm" />
            )}
            <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
            <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
          </div>
        </div>
      </div>
    </div>
  )
}

function formatPublishDate(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  // Parse date portion directly to avoid timezone shift
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return ''
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  if (isNaN(date.getTime())) return ''
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}
