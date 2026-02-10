import { Link } from 'react-router-dom'
import type { FeatureSetting } from '../types'
import StatusPill, { DatePill } from './StatusPill'
import { ArrowRightIcon, CogIcon } from './icons'

interface SettingsListProps {
  settings: FeatureSetting[]
  emptyMessage?: string
  compact?: boolean
}

export default function SettingsList({ settings, emptyMessage = 'No feature settings', compact = false }: SettingsListProps) {
  if (settings.length === 0) {
    return (
      <div className="text-center py-6">
        <CogIcon className="w-5 h-5 mx-auto text-zinc-700" />
        <p className="mt-2 text-xs text-zinc-500 font-mono">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      {settings.map((setting) => (
        <Link
          key={setting.setting_id}
          to={`/settings/${setting.setting_id}`}
          className="data-row group"
        >
          <div className="w-16 flex-shrink-0">
            <StatusPill status={setting.status} size="sm" showDot={false} />
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-sm text-zinc-300 group-hover:text-white transition-colors truncate block">
              {setting.name}
            </span>
            {!compact && setting.description && (
              <p className="mt-0.5 text-xs text-zinc-500 truncate">{setting.description}</p>
            )}
          </div>
          {!compact && (
            <>
              <ImpactBadges setting={setting} />
              <div className="hidden sm:flex items-center gap-3 flex-shrink-0">
                <DatePill label="B" date={setting.beta_date} variant="beta" />
                <DatePill label="P" date={setting.production_date} variant="prod" />
              </div>
            </>
          )}
          <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
        </Link>
      ))}
    </div>
  )
}

function ImpactBadges({ setting }: { setting: FeatureSetting }) {
  const badges: string[] = []

  if (setting.affects_ui) badges.push('UI')

  let areas: string[] = []
  if (setting.affected_areas) {
    try {
      areas = JSON.parse(setting.affected_areas)
    } catch {
      areas = setting.affected_areas.split(',').map(a => a.trim())
    }
  }

  if (badges.length === 0 && areas.length === 0) return null

  return (
    <div className="hidden md:flex items-center gap-1 flex-shrink-0">
      {setting.affects_ui && (
        <span className="pill bg-signal-cyan/10 text-signal-cyan">UI</span>
      )}
      {areas.slice(0, 2).map((area) => (
        <span key={area} className="pill bg-surface-3 text-zinc-500 max-w-[80px] truncate">
          {area}
        </span>
      ))}
      {areas.length > 2 && (
        <span className="text-xs font-mono text-zinc-500">+{areas.length - 2}</span>
      )}
    </div>
  )
}

export function SettingsListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="card overflow-hidden">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="data-row">
          <div className="w-16"><div className="skeleton h-4 w-12 rounded" /></div>
          <div className="flex-1"><div className="skeleton h-4 w-48" /></div>
        </div>
      ))}
    </div>
  )
}
