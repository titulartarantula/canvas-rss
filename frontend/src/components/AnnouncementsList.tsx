import type { Announcement } from '../types'
import { DocumentIcon, ExternalLinkIcon, CalendarIcon } from './icons'

interface AnnouncementsListProps {
  announcements: Announcement[]
  emptyMessage?: string
  showReleaseLink?: boolean
}

export default function AnnouncementsList({
  announcements, emptyMessage = 'No announcements', showReleaseLink = true,
}: AnnouncementsListProps) {
  if (announcements.length === 0) {
    return (
      <div className="text-center py-6">
        <DocumentIcon className="w-5 h-5 mx-auto text-zinc-700" />
        <p className="mt-2 text-xs text-zinc-500 font-mono">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {announcements.map((announcement, index) => (
        <AnnouncementCard key={announcement.id} announcement={announcement} index={index} showReleaseLink={showReleaseLink} />
      ))}
    </div>
  )
}

function AnnouncementCard({ announcement, index, showReleaseLink }: { announcement: Announcement; index: number; showReleaseLink: boolean }) {
  const aaStr = announcement.announced_at || ''
  const aaMatch = aaStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const announcedDate = aaMatch ? new Date(Number(aaMatch[1]), Number(aaMatch[2]) - 1, Number(aaMatch[3])) : new Date(aaStr)

  return (
    <div className="card p-4 animate-slide-up" style={{ animationDelay: `${index * 50}ms` }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
          <CalendarIcon className="w-3 h-3" />
          <time dateTime={announcement.announced_at}>
            {announcedDate.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
          </time>
          {announcement.section && (
            <>
              <span className="text-zinc-700">·</span>
              <span className="text-zinc-500">{announcement.section}</span>
            </>
          )}
        </div>
        {showReleaseLink && announcement.release_url && (
          <a href={announcement.release_url} target="_blank" rel="noopener noreferrer"
            className="text-zinc-600 hover:text-zinc-400 transition-colors">
            <ExternalLinkIcon className="w-3.5 h-3.5" />
          </a>
        )}
      </div>

      <h4 className="text-sm font-medium text-zinc-200">{announcement.h4_title}</h4>

      {announcement.category && (
        <span className="inline-block mt-1.5 pill bg-surface-3 text-zinc-500">{announcement.category}</span>
      )}
      {announcement.description && (
        <p className="mt-2 text-xs text-zinc-400 leading-relaxed">{announcement.description}</p>
      )}
      {announcement.implications && (
        <div className="mt-2 p-2.5 bg-status-beta/5 border-l-2 border-status-beta rounded-r-md">
          <p className="text-xs font-mono uppercase tracking-widest text-status-beta mb-1">Implications</p>
          <p className="text-xs text-zinc-400 leading-relaxed">{announcement.implications}</p>
        </div>
      )}
      {showReleaseLink && announcement.release_title && (
        <div className="mt-2 pt-2 border-t border-zinc-800/50">
          <p className="text-xs font-mono text-zinc-500">
            From: {announcement.release_url ? (
              <a href={announcement.release_url} target="_blank" rel="noopener noreferrer"
                className="text-signal-blue hover:text-signal-blue/80">{announcement.release_title}</a>
            ) : <span className="text-zinc-500">{announcement.release_title}</span>}
          </p>
        </div>
      )}
    </div>
  )
}

export function AnnouncementsListSkeleton({ count = 2 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4">
          <div className="flex items-center gap-2 mb-2"><div className="skeleton h-3 w-3" /><div className="skeleton h-3 w-28" /></div>
          <div className="skeleton h-4 w-48 mb-2" />
          <div className="skeleton h-3 w-full" />
        </div>
      ))}
    </div>
  )
}
