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
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Loading state
  if (isLoading) {
    return (
      <div className="animate-fade-in">
        <BackLink />
        <HeaderSkeleton />
        <div className="mt-10 grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-8">
            <Section title="Deployment Status">
              <DeploymentTimelineSkeleton />
            </Section>
            <Section title="Configuration">
              <ConfigurationTableSkeleton />
            </Section>
            <Section title="Announcement History">
              <AnnouncementsListSkeleton count={2} />
            </Section>
          </div>
          <div>
            <Section title="Community Activity">
              <CommunityPostsListSkeleton count={3} />
            </Section>
          </div>
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
          <p className="text-status-deprecated font-medium text-lg">Option not found</p>
          <p className="mt-2 text-ink-500">
            {error instanceof Error ? error.message : 'The requested feature option could not be loaded.'}
          </p>
          <Link
            to="/options"
            className="mt-6 inline-flex items-center gap-2 text-accent-primary hover:text-accent-primary/80 font-medium"
          >
            <ChevronLeftIcon className="w-4 h-4" />
            Back to Options
          </Link>
        </div>
      </div>
    )
  }

  const displayName = data.canonical_name || data.name
  const { announcements = [], community_posts = [] } = data

  return (
    <div className="animate-fade-in">
      {/* Back link */}
      <BackLink />

      {/* Header */}
      <header className="mt-6">
        <div className="flex items-start gap-4 flex-wrap">
          <h1 className="font-display text-display font-semibold text-ink-900">
            {displayName}
          </h1>
          <StatusPill status={data.status} size="md" />
        </div>

        {/* Breadcrumb - parent feature */}
        {data.feature && (
          <div className="mt-3 flex items-center gap-1.5 text-sm">
            <span className="text-ink-500">Part of</span>
            <Link
              to={`/features/${data.feature.feature_id}`}
              className="text-accent-primary hover:underline font-medium inline-flex items-center gap-1"
            >
              {data.feature.name}
              <ChevronRightIcon className="w-3 h-3" />
            </Link>
          </div>
        )}

        {/* Meta summary */}
        {data.meta_summary && (
          <p className="mt-4 text-ink-600 leading-relaxed max-w-3xl">
            {data.meta_summary}
          </p>
        )}

        {/* Description (if different from meta_summary) */}
        {data.description && data.description !== data.meta_summary && (
          <p className="mt-3 text-sm text-ink-500 leading-relaxed max-w-3xl">
            {data.description}
          </p>
        )}
      </header>

      {/* Divider */}
      <div className="mt-8 border-t border-ink-200" />

      {/* Main content grid */}
      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Left column - Timeline, Config, Announcements */}
        <div className="lg:col-span-2 space-y-10">
          {/* Deployment Timeline */}
          <Section
            title="Deployment Status"
            description="Track this option's journey through the release cycle"
          >
            <div className="card p-6">
              <DeploymentTimeline
                status={data.status}
                firstSeen={data.first_seen}
                betaDate={data.beta_date}
                productionDate={data.production_date}
                deprecationDate={data.deprecation_date}
              />
            </div>
          </Section>

          {/* Configuration */}
          <Section
            title="Configuration"
            description="How this option can be enabled and configured"
          >
            <div className="card p-5">
              <ConfigurationTable
                configuration={data.configuration}
                userGroupUrl={data.user_group_url}
              />
            </div>
          </Section>

          {/* Announcement History */}
          <Section
            title="Announcement History"
            count={announcements.length}
            description="When this option was mentioned in release notes"
          >
            <AnnouncementsList
              announcements={announcements}
              emptyMessage="No announcements found for this option"
            />
          </Section>
        </div>

        {/* Right column - Community Activity */}
        <div>
          <div className="lg:sticky lg:top-8">
            <Section
              title="Community Activity"
              count={community_posts.length}
              description="Related discussions and blog posts"
            >
              <CommunityPostsList
                posts={community_posts}
                emptyMessage="No community posts found"
              />
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}

function BackLink() {
  return (
    <Link
      to="/options"
      className="inline-flex items-center gap-1.5 text-sm text-ink-600 hover:text-ink-900 transition-colors"
    >
      <ChevronLeftIcon className="w-4 h-4" />
      Back to Options
    </Link>
  )
}

function Section({
  title,
  count,
  description,
  children,
}: {
  title: string
  count?: number
  description?: string
  children: React.ReactNode
}) {
  return (
    <section>
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <h2 className="font-display text-lg font-semibold text-ink-900">{title}</h2>
          {count !== undefined && count > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-ink-100 text-ink-600 rounded-full">
              {count}
            </span>
          )}
        </div>
        {description && (
          <p className="mt-1 text-sm text-ink-500">{description}</p>
        )}
      </div>
      {children}
    </section>
  )
}

function HeaderSkeleton() {
  return (
    <header className="mt-6">
      <div className="flex items-center gap-4">
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-6 w-20 rounded-full" />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <div className="skeleton h-4 w-48" />
      </div>
      <div className="mt-4 space-y-2">
        <div className="skeleton h-4 w-full max-w-2xl" />
        <div className="skeleton h-4 w-3/4 max-w-xl" />
      </div>
    </header>
  )
}
