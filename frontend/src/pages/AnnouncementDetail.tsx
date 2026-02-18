import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { announcementsApi } from '../api/client'
import StatusPill, { DatePill } from '../components/StatusPill'
import {
  ChevronLeftIcon,
  ExternalLinkIcon,
  ArrowRightIcon,
} from '../components/icons'

export default function AnnouncementDetail() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['announcement', id],
    queryFn: () => announcementsApi.get(Number(id)),
    enabled: !!id,
    staleTime: 1000 * 60 * 5,
  })

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6">
          <div className="skeleton h-5 w-24 mb-3 rounded" />
          <div className="skeleton h-7 w-96 mb-3" />
          <div className="skeleton h-4 w-full mt-4" />
          <div className="skeleton h-4 w-3/4 mt-2" />
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6 card p-8 text-center">
          <p className="text-signal-red text-sm">Announcement not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested announcement could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const isDeployNote = data.release_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy Note' : 'Release Note'

  // Build "View Online" URL: release_url + #anchor_id
  const onlineUrl = data.anchor_id
    ? `${data.release_url}#${data.anchor_id}`
    : data.release_url

  return (
    <div className="animate-fade-in">
      <BackLink contentId={data.content_id} releaseTitle={data.release_title} />

      <header className="mt-4">
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {data.section && (
            <span className="pill bg-surface-3 text-zinc-400">{data.section}</span>
          )}
          {data.category && (
            <span className="pill bg-surface-3 text-zinc-500">{data.category}</span>
          )}
          {data.option_status && <StatusPill status={data.option_status} size="sm" showDot={false} />}
        </div>
        <h1 className="mt-3 text-title text-zinc-100 leading-tight">{data.h4_title}</h1>
        <div className="mt-2 flex items-center gap-4">
          <a
            href={onlineUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors"
          >
            View Online <ExternalLinkIcon className="w-3 h-3" />
          </a>
          <span className="text-xs font-mono text-zinc-500">
            from {typeLabel}
          </span>
        </div>
      </header>

      {/* Description */}
      {data.description && (
        <div className="mt-6 card p-4">
          <p className="text-sm text-zinc-300 leading-relaxed">{data.description}</p>
        </div>
      )}

      {/* Dates */}
      <div className="mt-4 flex items-center gap-4">
        <DatePill label="Beta" date={data.beta_date || null} variant="beta" />
        <DatePill label="Prod" date={data.production_date || null} variant="prod" />
      </div>

      {/* Configuration details if available */}
      {(data.enable_location_account || data.enable_location_course) && (
        <div className="mt-6 card p-4">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-400 mb-3">Configuration</p>
          <div className="grid gap-2 text-xs font-mono">
            {data.enable_location_account && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Account</span>
                <span className="text-zinc-300">{data.enable_location_account}</span>
              </div>
            )}
            {data.enable_location_course && (
              <div className="flex justify-between">
                <span className="text-zinc-500">Course</span>
                <span className="text-zinc-300">{data.enable_location_course}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Related Feature */}
      {(data.option_id || data.setting_id) && (
        <div className="mt-6 card p-4">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-400 mb-3">Related Feature</p>
          {data.option_id && (
            <Link
              to={`/options/${data.option_id}`}
              className="flex items-center justify-between group"
            >
              <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
                {data.option_name || data.option_display_name || data.option_id}
              </span>
              <ArrowRightIcon className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
            </Link>
          )}
          {!data.option_id && data.setting_id && (
            <Link
              to={`/settings/${data.setting_id}`}
              className="flex items-center justify-between group"
            >
              <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
                {data.setting_name || data.setting_id}
              </span>
              <ArrowRightIcon className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300 transition-colors" />
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

function BackLink({ contentId, releaseTitle }: { contentId?: string; releaseTitle?: string }) {
  if (contentId) {
    return (
      <Link
        to={`/releases/${contentId}`}
        className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <ChevronLeftIcon className="w-3.5 h-3.5" />
        {releaseTitle || 'back to release'}
      </Link>
    )
  }
  return (
    <Link
      to="/"
      className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
    >
      <ChevronLeftIcon className="w-3.5 h-3.5" />
      dashboard
    </Link>
  )
}
