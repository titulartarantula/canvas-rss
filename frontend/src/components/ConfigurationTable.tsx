import { ExternalLinkIcon } from './icons'

interface Configuration {
  config_level: string | null
  default_state: string | null
  enable_location_account: string | null
  enable_location_course: string | null
  subaccount_config: boolean | null
  permissions: string | null
  affected_areas: string | null
  affects_ui: boolean | null
}

interface ConfigurationTableProps {
  configuration: Configuration
  userGroupUrl?: string | null
}

export default function ConfigurationTable({ configuration, userGroupUrl }: ConfigurationTableProps) {
  const rows = buildConfigRows(configuration, userGroupUrl)

  if (rows.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-ink-500">No configuration details available</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-ink-100">
      {rows.map((row) => (
        <div key={row.label} className="py-3 flex items-start gap-4">
          <dt className="w-40 flex-shrink-0 text-sm text-ink-500">
            {row.label}
          </dt>
          <dd className="flex-1 text-sm text-ink-800">
            {row.type === 'boolean' ? (
              <span className={`
                inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium
                ${row.value ? 'bg-status-released/10 text-status-released' : 'bg-ink-100 text-ink-500'}
              `}>
                <span className={`w-1.5 h-1.5 rounded-full ${row.value ? 'bg-status-released' : 'bg-ink-400'}`} />
                {row.value ? 'Yes' : 'No'}
              </span>
            ) : row.type === 'link' ? (
              <a
                href={row.value as string}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-accent-primary hover:underline"
              >
                View User Group
                <ExternalLinkIcon className="w-3.5 h-3.5" />
              </a>
            ) : row.type === 'tags' ? (
              <div className="flex flex-wrap gap-1.5">
                {(row.value as string[]).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 bg-ink-100 text-ink-700 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            ) : (
              <span className="font-medium">{row.value}</span>
            )}
          </dd>
        </div>
      ))}
    </div>
  )
}

type ConfigRow = {
  label: string
  value: string | string[] | boolean
  type: 'text' | 'boolean' | 'link' | 'tags'
}

function buildConfigRows(config: Configuration, userGroupUrl?: string | null): ConfigRow[] {
  const rows: ConfigRow[] = []

  if (config.config_level) {
    rows.push({
      label: 'Config Level',
      value: formatConfigLevel(config.config_level),
      type: 'text',
    })
  }

  if (config.default_state) {
    rows.push({
      label: 'Default State',
      value: formatDefaultState(config.default_state),
      type: 'text',
    })
  }

  if (config.enable_location_account) {
    rows.push({
      label: 'Account Setting',
      value: config.enable_location_account,
      type: 'text',
    })
  }

  if (config.enable_location_course) {
    rows.push({
      label: 'Course Setting',
      value: config.enable_location_course,
      type: 'text',
    })
  }

  if (config.subaccount_config !== null) {
    rows.push({
      label: 'Subaccount Config',
      value: config.subaccount_config,
      type: 'boolean',
    })
  }

  if (config.permissions) {
    rows.push({
      label: 'Permissions',
      value: config.permissions.split(',').map(p => p.trim()),
      type: 'tags',
    })
  }

  if (config.affected_areas) {
    rows.push({
      label: 'Affected Areas',
      value: config.affected_areas.split(',').map(a => a.trim()),
      type: 'tags',
    })
  }

  if (config.affects_ui !== null) {
    rows.push({
      label: 'Affects UI',
      value: config.affects_ui,
      type: 'boolean',
    })
  }

  if (userGroupUrl) {
    rows.push({
      label: 'User Group',
      value: userGroupUrl,
      type: 'link',
    })
  }

  return rows
}

function formatConfigLevel(level: string): string {
  const levels: Record<string, string> = {
    'site_admin': 'Site Admin',
    'root_account': 'Root Account',
    'account': 'Account',
    'course': 'Course',
  }
  return levels[level] || level
}

function formatDefaultState(state: string): string {
  const states: Record<string, string> = {
    'on': 'Enabled by Default',
    'off': 'Disabled by Default',
    'allowed': 'Allowed (Off by Default)',
    'hidden': 'Hidden',
  }
  return states[state] || state
}

// Skeleton for loading state
export function ConfigurationTableSkeleton() {
  return (
    <div className="divide-y divide-ink-100">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="py-3 flex items-start gap-4">
          <div className="w-40 skeleton h-4" />
          <div className="flex-1 skeleton h-4 w-32" />
        </div>
      ))}
    </div>
  )
}
