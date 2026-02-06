import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { releasesApi } from '../api/client'
import type { Announcement, UpcomingChange } from '../types'
import { DatePill } from '../components/StatusPill'
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
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Group announcements by section
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

  // Loading state
  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <HeaderSkeleton />
        <div className="mt-10 space-y-8">
          <SummarySkeleton />
          <AnnouncementsSkeleton />
        </div>
      </div>
    )
  }

  // Error state
  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-8 card p-12 text-center">
          <p className="text-status-deprecated font-medium text-lg">Release not found</p>
          <p className="mt-2 text-ink-500">
            {error instanceof Error ? error.message : 'The requested release could not be loaded.'}
          </p>
          <Link
            to="/releases"
            className="mt-6 inline-flex items-center gap-2 text-accent-primary hover:text-accent-primary/80 font-medium"
          >
            <ChevronLeftIcon className="w-4 h-4" />
            Back to Archive
          </Link>
        </div>
      </div>
    )
  }

  const isDeployNote = data.content_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy Notes' : 'Release Notes'
  const typeColor = isDeployNote ? 'text-status-optional bg-status-optional/10' : 'text-status-beta bg-status-beta/10'

  const publishDate = new Date(data.first_posted)
  const formattedDate = publishDate.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="animate-fade-in">
      {/* Back link */}
      <BackLink />

      {/* Header */}
      <header className="mt-6">
        {/* Type badge and date */}
        <div className="flex items-center gap-3 text-sm">
          <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold uppercase tracking-wide ${typeColor}`}>
            {typeLabel}
          </span>
          <span className="text-ink-400">·</span>
          <span className="text-ink-500 flex items-center gap-1.5">
            <CalendarIcon className="w-3.5 h-3.5" />
            {formattedDate}
          </span>
        </div>

        {/* Title */}
        <h1 className="mt-4 font-display text-display font-semibold text-ink-900 leading-tight">
          {data.title}
        </h1>

        {/* External link */}
        <a
          href={data.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-accent-primary hover:underline"
        >
          View original release notes
          <ExternalLinkIcon className="w-3.5 h-3.5" />
        </a>
      </header>

      {/* Summary */}
      {data.summary && (
        <section className="mt-8">
          <div className="card p-6 bg-gradient-to-br from-ink-50 to-white border-l-4 border-accent-primary">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-3">
              Summary
            </h2>
            <p className="text-ink-800 leading-relaxed">
              {data.summary}
            </p>
          </div>
        </section>
      )}

      {/* Divider */}
      <div className="mt-10 border-t border-ink-200" />

      {/* Main content grid */}
      <div className="mt-10 grid gap-10 lg:grid-cols-3">
        {/* Announcements - main column */}
        <div className="lg:col-span-2">
          {groupedAnnouncements.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-sm text-ink-500">No feature announcements in this release</p>
            </div>
          ) : (
            <div className="space-y-10">
              {groupedAnnouncements.map((group, groupIndex) => (
                <section key={group.section} className="animate-slide-up" style={{ animationDelay: `${groupIndex * 50}ms` }}>
                  {/* Section header */}
                  <div className="flex items-center gap-3 mb-4">
                    <h2 className="font-display text-lg font-semibold text-ink-900">
                      {group.section}
                    </h2>
                    <span className="px-2 py-0.5 text-xs font-medium bg-ink-100 text-ink-600 rounded-full">
                      {group.announcements.length}
                    </span>
                  </div>

                  {/* Announcements in this section */}
                  <div className="space-y-4">
                    {group.announcements.map((announcement, index) => (
                      <AnnouncementCard
                        key={announcement.id}
                        announcement={announcement}
                        index={index}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar - upcoming changes */}
        <div>
          <div className="lg:sticky lg:top-8">
            {data.upcoming_changes && data.upcoming_changes.length > 0 && (
              <UpcomingChangesSection changes={data.upcoming_changes} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function AnnouncementCard({ announcement, index }: { announcement: Announcement; index: number }) {
  return (
    <div
      className="card p-5 animate-slide-up"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* Category badge */}
      {announcement.category && (
        <span className="inline-block px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-ink-100 text-ink-600 rounded mb-3">
          {announcement.category}
        </span>
      )}

      {/* Title */}
      <h3 className="font-medium text-ink-900">
        {announcement.h4_title}
      </h3>

      {/* Description */}
      {announcement.description && (
        <p className="mt-2 text-sm text-ink-600 leading-relaxed">
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

      {/* Footer with dates and link */}
      <div className="mt-4 pt-3 border-t border-ink-100 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
          <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
        </div>

        {announcement.option_id && (
          <Link
            to={`/options/${announcement.option_id}`}
            className="inline-flex items-center gap-1 text-xs text-accent-primary hover:underline font-medium"
          >
            View option
            <ArrowRightIcon className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  )
}

function UpcomingChangesSection({ changes }: { changes: UpcomingChange[] }) {
  // Sort by date
  const sortedChanges = [...changes].sort((a, b) =>
    new Date(a.change_date).getTime() - new Date(b.change_date).getTime()
  )

  return (
    <section className="card p-5">
      <div className="flex items-center gap-2 mb-4">
        <ExclamationTriangleIcon className="w-4 h-4 text-status-pending" />
        <h2 className="font-display text-sm font-semibold text-ink-900 uppercase tracking-wide">
          Upcoming Changes
        </h2>
      </div>

      <div className="space-y-4">
        {sortedChanges.map((change, index) => {
          const changeDate = new Date(change.change_date)
          const isUpcoming = changeDate > new Date()
          const formattedDate = changeDate.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })

          return (
            <div
              key={index}
              className={`
                relative pl-4 border-l-2 transition-colors
                ${isUpcoming ? 'border-status-pending' : 'border-ink-200'}
              `}
            >
              <p className={`
                text-xs font-medium
                ${isUpcoming ? 'text-status-pending' : 'text-ink-500'}
              `}>
                {formattedDate}
              </p>
              <p className="mt-1 text-sm text-ink-700 leading-relaxed">
                {change.description}
              </p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function BackLink() {
  return (
    <Link
      to="/releases"
      className="inline-flex items-center gap-1.5 text-sm text-ink-600 hover:text-ink-900 transition-colors"
    >
      <ChevronLeftIcon className="w-4 h-4" />
      Back to Archive
    </Link>
  )
}

function HeaderSkeleton() {
  return (
    <header className="mt-6">
      <div className="flex items-center gap-3">
        <div className="skeleton h-6 w-24 rounded" />
        <div className="skeleton h-4 w-32" />
      </div>
      <div className="mt-4 skeleton h-8 w-96" />
      <div className="mt-4 skeleton h-4 w-48" />
    </header>
  )
}

function SummarySkeleton() {
  return (
    <div className="card p-6">
      <div className="skeleton h-3 w-16 mb-3" />
      <div className="space-y-2">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
      </div>
    </div>
  )
}

function AnnouncementsSkeleton() {
  return (
    <div className="space-y-8">
      <div>
        <div className="skeleton h-6 w-40 mb-4" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card p-5">
              <div className="skeleton h-4 w-16 mb-3 rounded" />
              <div className="skeleton h-5 w-64" />
              <div className="mt-2 space-y-2">
                <div className="skeleton h-4 w-full" />
                <div className="skeleton h-4 w-3/4" />
              </div>
              <div className="mt-4 pt-3 border-t border-ink-100 flex gap-4">
                <div className="skeleton h-4 w-20" />
                <div className="skeleton h-4 w-20" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
