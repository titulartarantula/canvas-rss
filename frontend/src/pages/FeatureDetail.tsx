import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { featuresApi } from '../api/client'
import OptionsList, { OptionsListSkeleton } from '../components/OptionsList'
import SettingsList, { SettingsListSkeleton } from '../components/SettingsList'
import AnnouncementsList, { AnnouncementsListSkeleton } from '../components/AnnouncementsList'
import CommunityPostsList, { CommunityPostsListSkeleton } from '../components/CommunityPostsList'
import InfoTooltip from '../components/InfoTooltip'
import { ChevronLeftIcon, AdjustmentsIcon, CogIcon } from '../components/icons'

export default function FeatureDetail() {
  const { featureId } = useParams<{ featureId: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['feature', featureId],
    queryFn: () => featuresApi.get(featureId!),
    enabled: !!featureId,
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
            <Section title="Feature Options"><OptionsListSkeleton count={3} /></Section>
            <Section title="Feature Settings"><SettingsListSkeleton count={3} /></Section>
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
          <p className="text-signal-red text-sm">Feature not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested feature could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const { options = [], settings = [], announcements = [], community_posts = [] } = data

  return (
    <div className="animate-fade-in">
      <BackLink />

      <header className="mt-4">
        <h1 className="text-title text-zinc-100">{data.name}</h1>
        <div className="mt-2 flex items-center gap-3 text-xs font-mono">
          {options.length > 0 && (
            <span className="inline-flex items-center gap-1 text-zinc-400">
              <AdjustmentsIcon className="w-3 h-3 text-signal-violet" />
              {options.length} {options.length === 1 ? 'option' : 'options'}
            </span>
          )}
          {settings.length > 0 && (
            <span className="inline-flex items-center gap-1 text-zinc-400">
              <CogIcon className="w-3 h-3 text-signal-cyan" />
              {settings.length} {settings.length === 1 ? 'setting' : 'settings'}
            </span>
          )}
          {data.status && data.status !== 'active' && (
            <span className="px-1.5 py-0.5 bg-surface-3 text-zinc-400 rounded text-xs uppercase">
              {data.status}
            </span>
          )}
        </div>
        {data.description && (
          <p className="mt-3 text-sm text-zinc-400 leading-relaxed max-w-3xl">
            {data.description}
          </p>
        )}
      </header>

      <div className="mt-6 border-t border-zinc-800/50" />

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-8">
          {options.length > 0 && (
            <Section
              title="Feature Options"
              count={options.length}
              icon={<AdjustmentsIcon className="w-3.5 h-3.5 text-signal-violet" />}
              tooltip={
                <InfoTooltip term="Feature Option">
                  <p>Admin toggles that can be enabled or disabled in Canvas Settings at the account or course level.</p>
                  <p>These require an administrator to activate them for your institution.</p>
                </InfoTooltip>
              }
            >
              <OptionsList options={options} emptyMessage="No feature options tracked" />
            </Section>
          )}

          {settings.length > 0 && (
            <Section
              title="Feature Settings"
              count={settings.length}
              icon={<CogIcon className="w-3.5 h-3.5 text-signal-cyan" />}
              tooltip={
                <InfoTooltip term="Feature Setting">
                  <p>Non-toggle changes like bug fixes, UI improvements, and backend enhancements.</p>
                  <p>These are applied automatically by Instructure — no admin action needed.</p>
                </InfoTooltip>
              }
            >
              <SettingsList settings={settings} emptyMessage="No feature settings tracked" />
            </Section>
          )}

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

function Section({ title, count, icon, tooltip, children }: { title: string; count?: number; icon?: React.ReactNode; tooltip?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        {icon}
        <h2 className="text-label uppercase text-zinc-400 font-mono">{title}</h2>
        {count !== undefined && count > 0 && (
          <span className="text-xs font-mono text-zinc-500">{count}</span>
        )}
        {tooltip}
      </div>
      {children}
    </section>
  )
}
