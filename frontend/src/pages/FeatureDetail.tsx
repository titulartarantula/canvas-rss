import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { featuresApi } from '../api/client'
import OptionsList, { OptionsListSkeleton } from '../components/OptionsList'
import AnnouncementsList, { AnnouncementsListSkeleton } from '../components/AnnouncementsList'
import CommunityPostsList, { CommunityPostsListSkeleton } from '../components/CommunityPostsList'
import { ChevronLeftIcon } from '../components/icons'

export default function FeatureDetail() {
  const { featureId } = useParams<{ featureId: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['feature', featureId],
    queryFn: () => featuresApi.get(featureId!),
    enabled: !!featureId,
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
            <Section title="Feature Options">
              <OptionsListSkeleton count={3} />
            </Section>
            <Section title="Recent Announcements">
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
          <p className="text-status-deprecated font-medium text-lg">Feature not found</p>
          <p className="mt-2 text-ink-500">
            {error instanceof Error ? error.message : 'The requested feature could not be loaded.'}
          </p>
          <Link
            to="/features"
            className="mt-6 inline-flex items-center gap-2 text-accent-primary hover:text-accent-primary/80 font-medium"
          >
            <ChevronLeftIcon className="w-4 h-4" />
            Back to Features
          </Link>
        </div>
      </div>
    )
  }

  const { options = [], announcements = [], community_posts = [] } = data

  return (
    <div className="animate-fade-in">
      {/* Back link */}
      <BackLink />

      {/* Header */}
      <header className="mt-6">
        <h1 className="font-display text-display font-semibold text-ink-900">
          {data.name}
        </h1>

        {/* Status and counts */}
        <div className="mt-3 flex items-center gap-4 text-sm">
          {options.length > 0 && (
            <span className="text-ink-600">
              <span className="font-medium text-ink-800">{options.length}</span>
              {' '}{options.length === 1 ? 'feature option' : 'feature options'}
            </span>
          )}
          {data.status && data.status !== 'active' && (
            <span className="px-2 py-0.5 text-xs font-medium uppercase tracking-wide bg-ink-100 text-ink-600 rounded">
              {data.status}
            </span>
          )}
        </div>

        {/* Description */}
        {data.description && (
          <p className="mt-4 text-ink-600 leading-relaxed max-w-3xl">
            {data.description}
          </p>
        )}
      </header>

      {/* Divider */}
      <div className="mt-8 border-t border-ink-200" />

      {/* Main content grid */}
      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Left column - Options and Announcements */}
        <div className="lg:col-span-2 space-y-10">
          {/* Feature Options */}
          <Section
            title="Feature Options"
            count={options.length}
            description="Configuration options available for this feature"
          >
            <OptionsList
              options={options}
              emptyMessage="No feature options are tracked for this feature"
            />
          </Section>

          {/* Announcements */}
          <Section
            title="Recent Announcements"
            count={announcements.length}
            description="Updates from Canvas release notes"
          >
            <AnnouncementsList
              announcements={announcements}
              emptyMessage="No announcements found for this feature"
            />
          </Section>
        </div>

        {/* Right column - Community Activity */}
        <div>
          <div className="lg:sticky lg:top-8">
            <Section
              title="Community Activity"
              count={community_posts.length}
              description="Related Q&A and blog posts"
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
      to="/features"
      className="inline-flex items-center gap-1.5 text-sm text-ink-600 hover:text-ink-900 transition-colors"
    >
      <ChevronLeftIcon className="w-4 h-4" />
      Back to Features
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
      <div className="skeleton h-8 w-64" />
      <div className="mt-3 flex items-center gap-4">
        <div className="skeleton h-5 w-32" />
      </div>
      <div className="mt-4 space-y-2">
        <div className="skeleton h-4 w-full max-w-2xl" />
        <div className="skeleton h-4 w-3/4 max-w-xl" />
      </div>
    </header>
  )
}
