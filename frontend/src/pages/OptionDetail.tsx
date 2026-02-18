import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { optionsApi } from '../api/client'
import StatusPill from '../components/StatusPill'
import DeploymentTimeline, { DeploymentTimelineSkeleton } from '../components/DeploymentTimeline'
import ConfigurationTable, { ConfigurationTableSkeleton } from '../components/ConfigurationTable'
import AnnouncementsList, { AnnouncementsListSkeleton } from '../components/AnnouncementsList'
import CommunityPostsList, { CommunityPostsListSkeleton } from '../components/CommunityPostsList'
import { ChevronLeftIcon, ChevronRightIcon } from '../components/icons'

export default function OptionDetail() {
  const { optionId } = useParams<{ optionId: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['option', optionId],
    queryFn: () => optionsApi.get(optionId!),
    enabled: !!optionId,
    staleTime: 1000 * 60 * 5,
  })

  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6">
          <div className="skeleton h-6 w-48 mb-2" />
          <div className="skeleton h-4 w-32 mb-6" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3 mt-6">
          <div className="lg:col-span-2 space-y-6">
            <Section title="Deployment"><DeploymentTimelineSkeleton /></Section>
            <Section title="Configuration"><ConfigurationTableSkeleton /></Section>
            <Section title="Announcements"><AnnouncementsListSkeleton count={2} /></Section>
          </div>
          <Section title="Community"><CommunityPostsListSkeleton count={3} /></Section>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <div className="mt-6 card p-8 text-center">
          <p className="text-signal-red text-sm">Option not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested option could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const displayName = data.canonical_name || data.name
  const { announcements = [], community_posts = [] } = data

  return (
    <div className="animate-fade-in">
      <BackLink />

      <header className="mt-4">
        <div className="flex items-center gap-3">
          <h1 className="text-title text-zinc-100">{displayName}</h1>
          <StatusPill status={data.status} size="md" />
        </div>

        {data.feature && (
          <div className="mt-2 flex items-center gap-1 text-xs font-mono">
            <span className="text-zinc-500">in</span>
            <Link
              to={`/features/${data.feature.feature_id}`}
              className="text-signal-blue hover:text-signal-blue/80 transition-colors inline-flex items-center gap-0.5"
            >
              {data.feature.name}
              <ChevronRightIcon className="w-3 h-3" />
            </Link>
          </div>
        )}

        {data.description && (
          <div className="mt-4">
            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
              Description
            </h3>
            <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
              {data.description}
            </p>
          </div>
        )}
        {data.meta_summary && (
          <div className="mt-4">
            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-1.5">
              Deployment Readiness
            </h3>
            <p className="text-sm text-zinc-400 leading-relaxed max-w-3xl">
              {data.meta_summary}
            </p>
          </div>
        )}
      </header>

      <div className="mt-6 border-t border-zinc-800/50" />

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          <Section title="Deployment Status">
            <div className="card p-5">
              <DeploymentTimeline
                status={data.status}
                firstSeen={data.first_seen}
                betaDate={data.beta_date}
                productionDate={data.production_date}
                deprecationDate={data.deprecation_date}
              />
            </div>
          </Section>

          <Section title="Configuration">
            <div className="card p-4">
              <ConfigurationTable
                configuration={data.configuration}
                userGroupUrl={data.user_group_url}
              />
            </div>
          </Section>

          <Section title="Announcements" count={announcements.length}>
            <AnnouncementsList announcements={announcements} emptyMessage="No announcements" />
          </Section>
        </div>

        <div>
          <div className="lg:sticky lg:top-16">
            <Section title="Community" count={community_posts.length}>
              <CommunityPostsList posts={community_posts} emptyMessage="No community posts" />
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/registry" className="inline-flex items-center gap-1 text-xs font-mono text-zinc-500 hover:text-zinc-300 transition-colors">
      <ChevronLeftIcon className="w-3.5 h-3.5" />
      registry
    </Link>
  )
}

function Section({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-label uppercase text-zinc-400 font-mono">{title}</h2>
        {count !== undefined && count > 0 && (
          <span className="text-xs font-mono text-zinc-500">{count}</span>
        )}
      </div>
      {children}
    </section>
  )
}
