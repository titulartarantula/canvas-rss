import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { releasesApi } from '../api/client'
import type { Announcement, UpcomingChange } from '../types'
import StatusPill, { DatePill } from '../components/StatusPill'
import {
  ChevronLeftIcon,
  ExternalLinkIcon,
  CalendarIcon,
  ArrowRightIcon,
  ExclamationTriangleIcon,
} from '../components/icons'

export default function ReleaseDetail() {
  const { contentId } = useParams<{ contentId: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['release', contentId],
    queryFn: () => releasesApi.get(contentId!),
    enabled: !!contentId,
    staleTime: 1000 * 60 * 5,
  })

  const groupedAnnouncements = useMemo(() => {
    if (!data?.announcements) return []
    const groups: { section: string; announcements: Announcement[] }[] = []
    const sectionMap = new Map<string, Announcement[]>()
    data.announcements.forEach(announcement => {
      const section = announcement.section || 'General'
      if (!sectionMap.has(section)) {
        sectionMap.set(section, [])
        groups.push({ section, announcements: sectionMap.get(section)! })
      }
      sectionMap.get(section)!.push(announcement)
    })
    return groups
  }, [data?.announcements])

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6">
          <div className="skeleton h-5 w-24 mb-3 rounded" />
          <div className="skeleton h-7 w-96 mb-3" />
          <div className="skeleton h-4 w-48" />
        </div>
        <div className="mt-8 space-y-4">
          <div className="card p-5"><div className="skeleton h-4 w-full" /><div className="mt-2 skeleton h-4 w-3/4" /></div>
          {[1, 2, 3].map(i => (<div key={i} className="card p-4"><div className="skeleton h-4 w-48 mb-2" /><div className="skeleton h-3 w-full" /></div>))}
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6 card p-8 text-center">
          <p className="text-signal-red text-sm">Release not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested release could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const isDeployNote = data.content_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy' : 'Release'
  const typeColor = isDeployNote ? 'text-status-optional bg-status-optional/15' : 'text-status-beta bg-status-beta/15'

  const pubStr = data.production_date || data.published_date || ''
  const pubMatch = pubStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const publishDate = pubMatch
    ? new Date(Number(pubMatch[1]), Number(pubMatch[2]) - 1, Number(pubMatch[3]))
    : new Date(pubStr)

  return (
    <div className="animate-fade-in">
      <BackLink />

      <header className="mt-4">
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className={`pill ${typeColor}`}>{typeLabel}</span>
          <span className="text-zinc-500 flex items-center gap-1">
            <CalendarIcon className="w-3 h-3" />
            {publishDate.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
        <h1 className="mt-3 text-title text-zinc-100 leading-tight">{data.title}</h1>
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors"
        >
          View Online <ExternalLinkIcon className="w-3 h-3" />
        </a>
      </header>

      {data.summary && (
        <div className="mt-6 card p-4 border-l-2 border-l-signal-blue bg-signal-blue/5">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-400 mb-2">Summary</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{data.summary}</p>
        </div>
      )}

      <div className="mt-8 border-t border-zinc-800/50" />

      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {groupedAnnouncements.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs text-zinc-500 font-mono">No feature announcements</p>
            </div>
          ) : (
            <div className="space-y-8">
              {groupedAnnouncements.map((group) => (
                <section key={group.section}>
                  <div className="flex items-center gap-2 mb-3">
                    <h2 className="text-label uppercase text-zinc-400 font-mono">{group.section}</h2>
                    <span className="text-xs font-mono text-zinc-500">{group.announcements.length}</span>
                  </div>
                  <div className="space-y-3">
                    {group.announcements.map((announcement) => (
                      <AnnouncementCard key={announcement.id} announcement={announcement} />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="lg:sticky lg:top-16">
            {data.upcoming_changes && data.upcoming_changes.length > 0 && (
              <UpcomingChangesSection changes={data.upcoming_changes} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function AnnouncementCard({ announcement }: { announcement: Announcement }) {
  return (
    <div className="card p-4">
      {announcement.category && (
        <span className="pill bg-surface-3 text-zinc-500 mb-2 inline-block">
          {announcement.category}
        </span>
      )}
      <Link
        to={`/announcements/${announcement.id}`}
        className="text-sm font-medium text-zinc-200 hover:text-white transition-colors"
      >
        {announcement.h4_title}
      </Link>
      {announcement.description && (
        <p className="mt-2 text-xs text-zinc-400 leading-relaxed">{announcement.description}</p>
      )}
      <div className="mt-3 pt-3 border-t border-zinc-800/50 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
          <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
          {announcement.option_status && <StatusPill status={announcement.option_status} size="sm" showDot={false} />}
        </div>
        {announcement.option_id && (
          <Link
            to={`/options/${announcement.option_id}`}
            className="text-xs font-mono text-signal-blue hover:text-signal-blue/80 inline-flex items-center gap-0.5"
          >
            view option <ArrowRightIcon className="w-3 h-3" />
          </Link>
        )}
        {!announcement.option_id && announcement.setting_id && (
          <Link
            to={`/settings/${announcement.setting_id}`}
            className="text-xs font-mono text-signal-cyan hover:text-signal-cyan/80 inline-flex items-center gap-0.5"
          >
            view setting <ArrowRightIcon className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  )
}

function UpcomingChangesSection({ changes }: { changes: UpcomingChange[] }) {
  const parseLocalDate = (dateStr: string): Date => {
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
    return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(dateStr)
  }
  const sortedChanges = [...changes].sort((a, b) =>
    parseLocalDate(a.change_date).getTime() - parseLocalDate(b.change_date).getTime()
  )

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-2">
        <ExclamationTriangleIcon className="w-3.5 h-3.5 text-signal-amber" />
        <span className="text-label uppercase text-zinc-400 font-mono">Upcoming Changes</span>
      </div>
      <div className="divide-y divide-zinc-800/30">
        {sortedChanges.map((change, index) => {
          const changeDate = parseLocalDate(change.change_date)
          const isUpcoming = changeDate > new Date()
          return (
            <div key={index} className={`px-4 py-3 border-l-2 ${isUpcoming ? 'border-l-signal-amber' : 'border-l-zinc-700'}`}>
              <p className={`text-xs font-mono ${isUpcoming ? 'text-signal-amber' : 'text-zinc-500'}`}>
                {changeDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
              <p className="mt-1 text-xs text-zinc-400 leading-relaxed">{change.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/releases" className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors">
      <ChevronLeftIcon className="w-3.5 h-3.5" />
      release history
    </Link>
  )
}
