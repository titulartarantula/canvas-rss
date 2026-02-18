import { useQuery } from '@tanstack/react-query'
import { useSearchParams, Link } from 'react-router-dom'
import { dashboardApi } from '../api/client'
import type { Release, Announcement, UpcomingChange, CommunityPost } from '../types'
import StatusPill, { DatePill } from '../components/StatusPill'
import DateNavigator from '../components/DateNavigator'
import {
  ExternalLinkIcon,
  ArrowRightIcon,
  ExclamationTriangleIcon,
  ChatBubbleIcon,
  DocumentIcon,
  BoltIcon,
  CubeIcon,
  SignalIcon,
} from '../components/icons'

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const dateParam = searchParams.get('date')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard', dateParam],
    queryFn: () => dashboardApi.get(dateParam || undefined),
    staleTime: 1000 * 60 * 5,
  })

  const handleDateChange = (newDate: string | null) => {
    if (newDate) {
      setSearchParams({ date: newDate })
    } else {
      setSearchParams({})
    }
  }

  if (isError) {
    return (
      <div className="animate-fade-in">
        <DateNavigator currentDate={dateParam} onDateChange={handleDateChange} />
        <div className="card p-8 text-center mt-4">
          <p className="text-signal-red font-medium text-sm">Failed to load dashboard</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'Please try again later'}
          </p>
        </div>
      </div>
    )
  }

  const releaseNote = data?.release_note
  const deployNote = data?.deploy_note
  const upcomingChanges = data?.upcoming_changes ?? []
  const recentActivity = data?.recent_activity ?? []

  return (
    <div className="animate-fade-in">
      <DateNavigator
        currentDate={dateParam}
        onDateChange={handleDateChange}
        isLoading={isLoading}
      />

      {/* Metric Cards Row */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4 mt-4">
        <MetricCard
          label="Release"
          value={releaseNote ? formatShortDate(releaseNote.production_date || releaseNote.published_date) : '--'}
          sub={releaseNote ? `${releaseNote.announcements?.length ?? 0} features` : 'No data'}
          color="blue"
          icon={<CubeIcon className="w-4 h-4" />}
          isLoading={isLoading}
        />
        <MetricCard
          label="Deploy"
          value={deployNote ? formatShortDate(deployNote.production_date || deployNote.published_date) : '--'}
          sub={deployNote ? `${deployNote.announcements?.length ?? 0} changes` : 'No data'}
          color="violet"
          icon={<BoltIcon className="w-4 h-4" />}
          isLoading={isLoading}
        />
        <MetricCard
          label="Upcoming"
          value={String(upcomingChanges.length)}
          sub={upcomingChanges.length > 0 ? `${upcomingChanges.length} change${upcomingChanges.length !== 1 ? 's' : ''}` : 'no changes'}
          color={upcomingChanges.length > 0 ? 'amber' : 'green'}
          icon={<ExclamationTriangleIcon className="w-4 h-4" />}
          isLoading={isLoading}
        />
        <MetricCard
          label="Activity"
          value={String(recentActivity.length)}
          sub="community posts"
          color="green"
          icon={<SignalIcon className="w-4 h-4" />}
          isLoading={isLoading}
        />
      </div>

      {/* Main Content: Two columns */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        {/* Left: Announcements Table */}
        <div className="lg:col-span-2 space-y-4">
          {/* Release Notes Table */}
          <AnnouncementsTable
            title="Release Notes"
            release={releaseNote}
            isLoading={isLoading}
          />

          {/* Deploy Notes Table */}
          <AnnouncementsTable
            title="Deploy Notes"
            release={deployNote}
            isLoading={isLoading}
          />

          {/* Recent Activity */}
          <ActivityTable posts={recentActivity} isLoading={isLoading} />
        </div>

        {/* Right: Upcoming Changes */}
        <div>
          <UpcomingPanel changes={upcomingChanges} isLoading={isLoading} />
        </div>
      </div>
    </div>
  )
}

// --- Metric Card ---
function MetricCard({
  label,
  value,
  sub,
  color,
  icon,
  isLoading,
}: {
  label: string
  value: string
  sub: string
  color: 'blue' | 'green' | 'amber' | 'red' | 'violet'
  icon: React.ReactNode
  isLoading?: boolean
}) {
  const colorMap = {
    blue: 'text-signal-blue shadow-glow-blue border-signal-blue/20',
    green: 'text-signal-green shadow-glow-green border-signal-green/20',
    amber: 'text-signal-amber shadow-glow-amber border-signal-amber/20',
    red: 'text-signal-red shadow-glow-red border-signal-red/20',
    violet: 'text-signal-violet shadow-glow-violet border-signal-violet/20',
  }

  const glowVars: Record<string, string> = {
    blue: 'rgba(59,130,246,0.06)',
    green: 'rgba(34,197,94,0.06)',
    amber: 'rgba(245,158,11,0.06)',
    red: 'rgba(239,68,68,0.06)',
    violet: 'rgba(139,92,246,0.06)',
  }

  return (
    <div
      className={`metric-card p-4 ${colorMap[color]} animate-slide-up`}
      style={{ '--glow-color': glowVars[color] } as React.CSSProperties}
    >
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <span className="text-label uppercase text-zinc-400 font-mono">{label}</span>
          <span className={colorMap[color].split(' ')[0]}>{icon}</span>
        </div>
        {isLoading ? (
          <div className="skeleton h-7 w-16 mb-1" />
        ) : (
          <p className={`text-metric font-mono ${colorMap[color].split(' ')[0]}`}>{value}</p>
        )}
        <p className="text-xs text-zinc-400 font-mono mt-1">{isLoading ? '' : sub}</p>
      </div>
    </div>
  )
}

// --- Announcements Table ---
function AnnouncementsTable({
  title,
  release,
  isLoading,
}: {
  title: string
  release: Release | null | undefined
  isLoading: boolean
}) {
  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center justify-between">
          <h2 className="text-label uppercase text-zinc-400 font-mono">{title}</h2>
        </div>
        <div className="divide-y divide-zinc-800/30">
          {[1, 2, 3].map(i => (
            <div key={i} className="px-4 py-3">
              <div className="skeleton h-4 w-48 mb-2" />
              <div className="skeleton h-3 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (!release || !release.announcements?.length) {
    return (
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center justify-between">
          <h2 className="text-label uppercase text-zinc-400 font-mono">{title}</h2>
        </div>
        <div className="px-4 py-6 text-center">
          <p className="text-xs text-zinc-500 font-mono">No data for this period</p>
        </div>
      </div>
    )
  }

  const announcements = release.announcements || []

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-label uppercase text-zinc-400 font-mono">{title}</h2>
          <span className="text-xs font-mono text-zinc-400">
            {formatShortDate(release.production_date || release.published_date)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/releases/${release.source_id}`}
            className="text-xs font-mono text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            view all
          </Link>
          <a
            href={release.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors flex items-center gap-1"
          >
            View Online
            <ExternalLinkIcon className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Announcement rows */}
      <div>
        {announcements.slice(0, 6).map((announcement, idx) => (
          <AnnouncementRow key={announcement.id || idx} announcement={announcement} />
        ))}
        {announcements.length > 6 && (
          <Link
            to={`/releases/${release.source_id}`}
            className="data-row text-xs font-mono text-zinc-500 hover:text-zinc-300 justify-center"
          >
            +{announcements.length - 6} more
            <ArrowRightIcon className="w-3 h-3 ml-1" />
          </Link>
        )}
      </div>
    </div>
  )
}

function AnnouncementRow({ announcement }: { announcement: Announcement }) {
  return (
    <div className="data-row">
      {/* Status */}
      <div className="w-20 flex-shrink-0">
        {announcement.option_status ? (
          <StatusPill status={announcement.option_status} size="sm" showDot={false} />
        ) : (
          <span className="text-xs font-mono text-zinc-500">--</span>
        )}
      </div>

      {/* Title & Description */}
      <div className="flex-1 min-w-0">
        <Link
          to={`/announcements/${announcement.id}`}
          className="text-sm text-zinc-300 truncate block hover:text-white transition-colors"
        >
          {announcement.h4_title}
        </Link>
        {announcement.description && (
          <p className="text-xs text-zinc-500 mt-0.5 line-clamp-4">{announcement.description}</p>
        )}
      </div>

      {/* Dates */}
      <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
        <DatePill label="Beta" date={announcement.beta_date || null} variant="beta" />
        <DatePill label="Prod" date={announcement.production_date || null} variant="prod" />
      </div>
    </div>
  )
}

// --- Upcoming Changes Panel ---
function UpcomingPanel({ changes, isLoading }: { changes: UpcomingChange[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800/50">
          <h2 className="text-label uppercase text-zinc-400 font-mono">Upcoming Changes</h2>
        </div>
        <div className="p-4 space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i}>
              <div className="skeleton h-3 w-24 mb-1" />
              <div className="skeleton h-4 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

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
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center gap-2">
        <h2 className="text-label uppercase text-zinc-400 font-mono">Upcoming Changes</h2>
        {changes.length > 0 && (
          <span className="px-1.5 py-0.5 text-xs font-mono font-medium bg-signal-amber/15 text-signal-amber rounded">
            {changes.length}
          </span>
        )}
      </div>

      {changes.length === 0 ? (
        <div className="p-6 text-center">
          <p className="text-xs text-zinc-500 font-mono">No upcoming changes</p>
        </div>
      ) : (
        <div className="divide-y divide-zinc-800/30">
          {sortedChanges.map((change, idx) => {
            const changeDate = parseLocalDate(change.change_date)
            const daysUntil = Math.ceil((changeDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
            const isPast = daysUntil < 0
            const isUrgent = daysUntil <= 7 && !isPast
            const isWarning = daysUntil <= 30 && !isPast

            const urgencyColor = isPast
              ? 'border-l-zinc-600'
              : isUrgent
                ? 'border-l-signal-red'
                : isWarning
                  ? 'border-l-signal-amber'
                  : 'border-l-zinc-700'

            return (
              <div key={idx} className={`px-4 py-3 border-l-2 ${urgencyColor}`}>
                <div className="flex items-center gap-2 mb-1">
                  {isUrgent && <ExclamationTriangleIcon className="w-3 h-3 text-signal-red" />}
                  <span className={`text-xs font-mono ${isPast ? 'text-zinc-500' : isUrgent ? 'text-signal-red' : isWarning ? 'text-signal-amber' : 'text-zinc-400'}`}>
                    {changeDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  {!isPast && (
                    <span className="text-xs font-mono text-zinc-500">
                      {daysUntil === 0 ? 'today' : daysUntil === 1 ? 'tomorrow' : `${daysUntil}d`}
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {change.description}
                </p>
              </div>
            )
          })}
          <div className="px-4 py-3">
            <a href="https://community.instructure.com/en/kb/articles/664261-instructure-enforcements-deprecations-and-breaking-changes" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors">
              See all upcoming changes <ExternalLinkIcon className="w-3 h-3" />
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Activity Table ---
function ActivityTable({ posts, isLoading }: { posts: CommunityPost[]; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-800/50">
          <h2 className="text-label uppercase text-zinc-400 font-mono">Recent Activity</h2>
        </div>
        <div className="divide-y divide-zinc-800/30">
          {[1, 2, 3].map(i => (
            <div key={i} className="px-4 py-3 flex items-center gap-3">
              <div className="skeleton w-6 h-6 rounded" />
              <div className="flex-1">
                <div className="skeleton h-4 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (posts.length === 0) return null

  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-3 border-b border-zinc-800/50 flex items-center justify-between">
        <h2 className="text-label uppercase text-zinc-400 font-mono">Recent Activity</h2>
        <span className="text-xs font-mono text-zinc-400">{posts.length} posts</span>
      </div>

      <div>
        {posts.slice(0, 8).map((post) => {
          const isQuestion = post.content_type === 'question'
          return (
            <a
              key={post.source_id}
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              className="data-row group"
            >
              {/* Type icon */}
              <div className="flex-shrink-0">
                {isQuestion ? (
                  <ChatBubbleIcon className="w-3.5 h-3.5 text-status-optional" />
                ) : (
                  <DocumentIcon className="w-3.5 h-3.5 text-status-preview" />
                )}
              </div>

              {/* Type label */}
              <div className="w-10 flex-shrink-0">
                <span className={`text-xs font-mono font-medium uppercase ${isQuestion ? 'text-status-optional' : 'text-status-preview'}`}>
                  {isQuestion ? 'Q&A' : 'Blog'}
                </span>
              </div>

              {/* Title */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors truncate">
                  {post.title}
                </p>
              </div>

              {/* Time */}
              <span className="text-xs font-mono text-zinc-500 flex-shrink-0 hidden sm:block">
                {formatRelativeTime(post.first_posted)}
              </span>
            </a>
          )
        })}
      </div>
    </div>
  )
}

// --- Helpers ---
function formatShortDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--'
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return '--'
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'today'
  if (diffDays === 1) return '1d ago'
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`
  return `${Math.floor(diffDays / 30)}mo ago`
}
