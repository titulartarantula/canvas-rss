import type { Announcement } from '../types'
import { DocumentIcon, ExternalLinkIcon, CalendarIcon } from './icons'

interface AnnouncementsListProps {
  announcements: Announcement[]
  emptyMessage?: string
  showReleaseLink?: boolean
}

export default function AnnouncementsList({
  announcements,
  emptyMessage = 'No announcements',
  showReleaseLink = true,
}: AnnouncementsListProps) {
  if (announcements.length === 0) {
    return (
      <div className="text-center py-8">
        <DocumentIcon className="w-8 h-8 mx-auto text-ink-300" />
        <p className="mt-2 text-sm text-ink-500">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {announcements.map((announcement, index) => (
        <AnnouncementCard
          key={announcement.id}
          announcement={announcement}
          index={index}
          showReleaseLink={showReleaseLink}
        />
      ))}
    </div>
  )
}

function AnnouncementCard({
  announcement,
  index,
  showReleaseLink,
}: {
  announcement: Announcement
  index: number
  showReleaseLink: boolean
}) {
  const aaStr = announcement.announced_at || ''
  const aaMatch = aaStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const announcedDate = aaMatch
    ? new Date(Number(aaMatch[1]), Number(aaMatch[2]) - 1, Number(aaMatch[3]))
    : new Date(aaStr)

  return (
    <div
      className="card p-4 animate-slide-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Header with date and source */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex items-center gap-2 text-xs text-ink-500">
          <CalendarIcon className="w-3.5 h-3.5" />
          <time dateTime={announcement.announced_at}>
            {announcedDate.toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </time>
          {announcement.section && (
            <>
              <span className="text-ink-300">·</span>
              <span className="text-ink-600">{announcement.section}</span>
            </>
          )}
        </div>

        {showReleaseLink && announcement.release_url && (
          <a
            href={announcement.release_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink-400 hover:text-ink-600 transition-colors"
            title="View release notes"
          >
            <ExternalLinkIcon className="w-4 h-4" />
          </a>
        )}
      </div>

      {/* Title */}
      <h4 className="font-medium text-ink-900">
        {announcement.h4_title}
      </h4>

      {/* Category badge */}
      {announcement.category && (
        <span className="inline-block mt-2 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-ink-100 text-ink-600 rounded">
          {announcement.category}
        </span>
      )}

      {/* Description */}
      {announcement.description && (
        <p className="mt-3 text-sm text-ink-600 leading-relaxed">
          {announcement.description}
        </p>
      )}

      {/* Implications */}
      {announcement.implications && (
        <div className="mt-3 p-3 bg-status-beta/5 border-l-2 border-status-beta rounded-r-lg">
          <p className="text-xs font-medium text-status-beta uppercase tracking-wide mb-1">
            Implications
          </p>
          <p className="text-sm text-ink-700 leading-relaxed">
            {announcement.implications}
          </p>
        </div>
      )}

      {/* Release source link */}
      {showReleaseLink && announcement.release_title && (
        <div className="mt-3 pt-3 border-t border-ink-100">
          <p className="text-xs text-ink-500">
            From:{' '}
            {announcement.release_url ? (
              <a
                href={announcement.release_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-primary hover:underline"
              >
                {announcement.release_title}
              </a>
            ) : (
              <span className="text-ink-700">{announcement.release_title}</span>
            )}
          </p>
        </div>
      )}
    </div>
  )
}

// Skeleton for loading state
export function AnnouncementsListSkeleton({ count = 2 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="skeleton h-3 w-3" />
            <div className="skeleton h-3 w-32" />
          </div>
          <div className="skeleton h-5 w-64" />
          <div className="mt-3 space-y-2">
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-3/4" />
          </div>
        </div>
      ))}
    </div>
  )
}
