import { ExternalLinkIcon } from './icons'

interface Configuration {
  prod_account_state: string
  prod_course_state: string
  beta_account_state: string
  beta_course_state: string
}

interface ConfigurationTableProps {
  configuration: Configuration
  userGroupUrl?: string | null
}

export default function ConfigurationTable({ configuration, userGroupUrl }: ConfigurationTableProps) {
  const rows = buildConfigRows(configuration, userGroupUrl)
  if (rows.length === 0) {
    return <div className="text-center py-6"><p className="text-xs text-zinc-500 font-mono">No configuration details</p></div>
  }

  return (
    <div className="divide-y divide-zinc-800/50">
      {rows.map((row) => (
        <div key={row.label} className="py-2.5 flex items-start gap-4">
          <dt className="w-36 flex-shrink-0 text-xs font-mono text-zinc-500">{row.label}</dt>
          <dd className="flex-1 text-sm text-zinc-300">
            {row.type === 'link' ? (
              <a href={row.value as string} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-signal-blue hover:text-signal-blue/80 text-xs font-mono">
                User Group <ExternalLinkIcon className="w-3 h-3" />
              </a>
            ) : (
              <span className="text-xs font-mono">{row.value}</span>
            )}
          </dd>
        </div>
      ))}
    </div>
  )
}

type ConfigRow = { label: string; value: string; type: 'text' | 'link' }

function formatState(state: string): string {
  const states: Record<string, string> = {
    'enabled_unlocked': 'Enabled / Unlocked',
    'enabled_locked': 'Enabled / Locked',
    'disabled_unlocked': 'Disabled / Unlocked',
    'disabled_locked': 'Disabled / Locked',
    'enabled': 'Enabled (account-only)',
    'disabled': 'Disabled (account-only)',
    'csm_managed': 'CSM Managed',
    'lti_required': 'LTI Required',
    'user_setting': 'User Setting',
  }
  return states[state] || state
}

function buildConfigRows(config: Configuration, userGroupUrl?: string | null): ConfigRow[] {
  const rows: ConfigRow[] = []

  if (config.prod_account_state && config.prod_account_state !== 'N/A')
    rows.push({ label: 'Prod Account', value: formatState(config.prod_account_state), type: 'text' })
  if (config.prod_course_state && config.prod_course_state !== 'N/A')
    rows.push({ label: 'Prod Course', value: formatState(config.prod_course_state), type: 'text' })
  if (config.beta_account_state && config.beta_account_state !== 'N/A')
    rows.push({ label: 'Beta Account', value: formatState(config.beta_account_state), type: 'text' })
  if (config.beta_course_state && config.beta_course_state !== 'N/A')
    rows.push({ label: 'Beta Course', value: formatState(config.beta_course_state), type: 'text' })
  if (userGroupUrl)
    rows.push({ label: 'User Group', value: userGroupUrl, type: 'link' })

  return rows
}

export function ConfigurationTableSkeleton() {
  return (
    <div className="card p-4 divide-y divide-zinc-800/50">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="py-2.5 flex items-start gap-4">
          <div className="w-36 skeleton h-3" />
          <div className="flex-1 skeleton h-3 w-24" />
        </div>
      ))}
    </div>
  )
}
