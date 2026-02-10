import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { settingsApi } from '../api/client'
import StatusPill from '../components/StatusPill'
import DeploymentTimeline, { DeploymentTimelineSkeleton } from '../components/DeploymentTimeline'
import AnnouncementsList, { AnnouncementsListSkeleton } from '../components/AnnouncementsList'
import CommunityPostsList, { CommunityPostsListSkeleton } from '../components/CommunityPostsList'
import InfoTooltip from '../components/InfoTooltip'
import { ChevronLeftIcon, ChevronRightIcon, CogIcon } from '../components/icons'

export default function SettingDetail() {
  const { settingId } = useParams<{ settingId: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['setting', settingId],
    queryFn: () => settingsApi.get(settingId!),
    enabled: !!settingId,
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
            <Section title="Impact"><ImpactSkeleton /></Section>
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
          <p className="text-signal-red text-sm">Setting not found</p>
          <p className="mt-1 text-xs text-zinc-500">
            {error instanceof Error ? error.message : 'The requested setting could not be loaded.'}
          </p>
        </div>
      </div>
    )
  }

  const { announcements = [], community_posts = [] } = data

  // Parse affected areas and roles
  let affectedAreas: string[] = []
  let affectedRoles: string[] = []
  try {
    if (data.affected_areas) affectedAreas = JSON.parse(data.affected_areas)
  } catch {
    if (data.affected_areas) affectedAreas = data.affected_areas.split(',').map(a => a.trim())
  }
  try {
    if (data.affects_roles) affectedRoles = JSON.parse(data.affects_roles)
  } catch {
    if (data.affects_roles) affectedRoles = data.affects_roles.split(',').map(r => r.trim())
  }

  return (
    <div className="animate-fade-in">
      <BackLink />

      <header className="mt-4">
        <div className="flex items-center gap-3">
          <CogIcon className="w-5 h-5 text-signal-cyan flex-shrink-0" />
          <h1 className="text-title text-zinc-100">{data.name}</h1>
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

        {data.meta_summary && (
          <p className="mt-3 text-sm text-zinc-400 leading-relaxed max-w-3xl">
            {data.meta_summary}
          </p>
        )}
        {data.description && data.description !== data.meta_summary && (
          <p className="mt-2 text-xs text-zinc-500 leading-relaxed max-w-3xl">
            {data.description}
          </p>
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
                deprecationDate={null}
              />
            </div>
          </Section>

          <Section
            title="Impact"
            tooltip={
              <InfoTooltip term="Impact">
                <p>Shows which parts of Canvas this change affects, whether it changes the UI, and which user roles are impacted.</p>
              </InfoTooltip>
            }
          >
            <ImpactTable
              affectedAreas={affectedAreas}
              affectsUi={data.affects_ui}
              affectedRoles={affectedRoles}
            />
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

function ImpactTable({
  affectedAreas,
  affectsUi,
  affectedRoles,
}: {
  affectedAreas: string[]
  affectsUi: boolean | null
  affectedRoles: string[]
}) {
  const hasData = affectedAreas.length > 0 || affectsUi !== null || affectedRoles.length > 0

  if (!hasData) {
    return (
      <div className="card p-6 text-center">
        <p className="text-xs text-zinc-500 font-mono">No impact data available</p>
      </div>
    )
  }

  return (
    <div className="card p-4">
      <div className="divide-y divide-zinc-800/50">
        {affectsUi !== null && (
          <div className="py-2.5 flex items-start gap-4">
            <dt className="w-32 flex-shrink-0 text-xs font-mono text-zinc-500">Affects UI</dt>
            <dd className="flex-1">
              <span className={`pill ${affectsUi ? 'bg-signal-cyan/15 text-signal-cyan' : 'bg-surface-3 text-zinc-500'}`}>
                {affectsUi ? 'Yes' : 'No'}
              </span>
            </dd>
          </div>
        )}
        {affectedAreas.length > 0 && (
          <div className="py-2.5 flex items-start gap-4">
            <dt className="w-32 flex-shrink-0 text-xs font-mono text-zinc-500">Affected Areas</dt>
            <dd className="flex-1">
              <div className="flex flex-wrap gap-1">
                {affectedAreas.map((area) => (
                  <span key={area} className="pill bg-surface-3 text-zinc-400">{area}</span>
                ))}
              </div>
            </dd>
          </div>
        )}
        {affectedRoles.length > 0 && (
          <div className="py-2.5 flex items-start gap-4">
            <dt className="w-32 flex-shrink-0 text-xs font-mono text-zinc-500">Affected Roles</dt>
            <dd className="flex-1">
              <div className="flex flex-wrap gap-1">
                {affectedRoles.map((role) => (
                  <span key={role} className="pill bg-signal-violet/10 text-signal-violet">{role}</span>
                ))}
              </div>
            </dd>
          </div>
        )}
      </div>
    </div>
  )
}

function ImpactSkeleton() {
  return (
    <div className="card p-4 divide-y divide-zinc-800/50">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="py-2.5 flex items-start gap-4">
          <div className="w-32 skeleton h-3" />
          <div className="flex-1 skeleton h-3 w-24" />
        </div>
      ))}
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

function Section({ title, count, tooltip, children }: { title: string; count?: number; tooltip?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
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
