import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { settingsApi } from '../api/client'
import type { FeatureSetting } from '../types'
import StatusFilter from '../components/StatusFilter'
import SortSelect from '../components/SortSelect'
import StatusPill, { DatePill } from '../components/StatusPill'
import { SearchIcon, XMarkIcon, ArrowRightIcon, CogIcon } from '../components/icons'

const SETTING_STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'beta', label: 'Beta', color: 'bg-status-beta' },
  { value: 'active', label: 'Released', color: 'bg-status-released' },
  { value: 'pending', label: 'Pending', color: 'bg-status-pending' },
  { value: 'deprecated', label: 'Deprecated', color: 'bg-status-deprecated' },
]

export default function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') || ''
  const sort = searchParams.get('sort') || 'updated'
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['settings', { status, sort }],
    queryFn: () => settingsApi.list({ status: status || undefined, sort }),
    staleTime: 1000 * 60 * 5,
  })

  const updateParams = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value) { newParams.set(key, value) } else { newParams.delete(key) }
    })
    setSearchParams(newParams)
  }

  const filteredSettings = useMemo(() => {
    if (!data?.settings) return []
    if (!searchQuery.trim()) return data.settings
    const query = searchQuery.toLowerCase()
    return data.settings.filter(setting => {
      const name = setting.name.toLowerCase()
      const desc = (setting.description || setting.meta_summary || '').toLowerCase()
      const feature = (setting.feature_name || '').toLowerCase()
      return name.includes(query) || desc.includes(query) || feature.includes(query)
    })
  }, [data?.settings, searchQuery])

  const totalCount = data?.settings?.length || 0

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Feature Settings</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : (
              searchQuery
                ? `${filteredSettings.length} of ${totalCount} settings`
                : `${totalCount} settings`
            )}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="space-y-3 mb-6">
        <div className="relative max-w-sm">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search settings..."
            className="w-full pl-9 pr-8 py-2 text-sm bg-surface-2 border border-zinc-800 rounded-md
                       text-zinc-300 placeholder:text-zinc-600 font-mono
                       focus:outline-none focus:border-zinc-600 focus-visible:ring-2 focus-visible:ring-signal-blue/40 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400">
              <XMarkIcon className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <StatusFilter
            value={status}
            onChange={(newStatus) => updateParams({ status: newStatus })}
            options={SETTING_STATUS_OPTIONS}
          />
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-400">sort</span>
            <SortSelect value={sort} onChange={(newSort) => updateParams({ sort: newSort })} />
          </div>
        </div>
      </div>

      {/* Settings table */}
      <div className="card overflow-hidden">
        {/* Table header */}
        <div className="px-4 py-2.5 border-b border-zinc-800/50 flex items-center gap-4 text-xs font-mono uppercase tracking-widest text-zinc-400">
          <span className="w-20">Status</span>
          <span className="flex-1">Name</span>
          <span className="hidden sm:block w-28">Feature</span>
          <span className="hidden md:block w-24">Prod Date</span>
          <span className="w-4" />
        </div>

        {isLoading ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="data-row">
              <div className="w-20"><div className="skeleton h-4 w-14 rounded" /></div>
              <div className="flex-1"><div className="skeleton h-4 w-48" /></div>
              <div className="hidden sm:block w-28"><div className="skeleton h-3 w-20" /></div>
            </div>
          ))
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-signal-red text-sm">Failed to load settings</p>
          </div>
        ) : filteredSettings.length === 0 ? (
          <div className="p-8 text-center">
            <CogIcon className="w-6 h-6 mx-auto text-zinc-700" />
            <p className="mt-2 text-sm text-zinc-500">No settings found</p>
            {(status || searchQuery) && (
              <button
                onClick={() => { setSearchQuery(''); updateParams({ status: '' }) }}
                className="mt-3 text-xs font-mono text-signal-blue hover:text-signal-blue/80"
              >
                clear filters
              </button>
            )}
          </div>
        ) : (
          filteredSettings.map((setting) => (
            <SettingRow key={setting.setting_id} setting={setting} />
          ))
        )}
      </div>
    </div>
  )
}

function SettingRow({ setting }: { setting: FeatureSetting }) {
  return (
    <Link to={`/settings/${setting.setting_id}`} className="data-row group">
      <div className="w-20 flex-shrink-0">
        <StatusPill status={setting.status} size="sm" showDot={false} />
      </div>

      <div className="flex-1 min-w-0">
        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors truncate block">
          {setting.name}
        </span>
      </div>

      <div className="hidden sm:block w-28 flex-shrink-0">
        {setting.feature_name && (
          <span className="text-xs font-mono text-zinc-500 truncate block">
            {setting.feature_name}
          </span>
        )}
      </div>

      <div className="hidden md:flex items-center w-24 flex-shrink-0">
        <DatePill label="P" date={setting.production_date} variant="prod" />
      </div>

      <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
    </Link>
  )
}
