import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { optionsApi } from '../api/client'
import type { FeatureOption } from '../types'
import StatusFilter, { LIFECYCLE_OPTIONS } from '../components/StatusFilter'
import SortSelect from '../components/SortSelect'
import StatusPill, { DatePill } from '../components/StatusPill'
import { SearchIcon, XMarkIcon, ArrowRightIcon, AdjustmentsIcon } from '../components/icons'

export default function Options() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('lifecycle_stage') || ''
  const sort = searchParams.get('sort') || 'updated'
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['options', { status, sort }],
    queryFn: () => optionsApi.list({ lifecycle_stage: status || undefined, sort }),
    staleTime: 1000 * 60 * 5,
  })

  const updateParams = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value) { newParams.set(key, value) } else { newParams.delete(key) }
    })
    setSearchParams(newParams)
  }

  const filteredOptions = useMemo(() => {
    if (!data?.options) return []
    if (!searchQuery.trim()) return data.options
    const query = searchQuery.toLowerCase()
    return data.options.filter(option => {
      const name = (option.canonical_name || option.name).toLowerCase()
      const desc = (option.description || option.meta_summary || '').toLowerCase()
      const feature = (option.feature_name || '').toLowerCase()
      return name.includes(query) || desc.includes(query) || feature.includes(query)
    })
  }, [data?.options, searchQuery])

  const totalCount = data?.options?.length || 0

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Feature Options</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : (
              searchQuery
                ? `${filteredOptions.length} of ${totalCount} options`
                : `${totalCount} options`
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
            placeholder="Search options..."
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
            onChange={(newStatus) => updateParams({ lifecycle_stage: newStatus })}
            options={LIFECYCLE_OPTIONS}
          />
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-400">sort</span>
            <SortSelect value={sort} onChange={(newSort) => updateParams({ sort: newSort })} />
          </div>
        </div>
      </div>

      {/* Options table */}
      <div className="card overflow-hidden">
        {/* Table header */}
        <div className="px-4 py-2.5 border-b border-zinc-800/50 flex items-center gap-4 text-xs font-mono uppercase tracking-widest text-zinc-400">
          <span className="w-20">Status</span>
          <span className="flex-1">Name</span>
          <span className="hidden sm:block w-28">Feature</span>
          <span className="hidden md:block w-32">Dates</span>
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
            <p className="text-signal-red text-sm">Failed to load options</p>
          </div>
        ) : filteredOptions.length === 0 ? (
          <div className="p-8 text-center">
            <AdjustmentsIcon className="w-6 h-6 mx-auto text-zinc-700" />
            <p className="mt-2 text-sm text-zinc-500">No options found</p>
            {(status || searchQuery) && (
              <button
                onClick={() => { setSearchQuery(''); updateParams({ lifecycle_stage: '' }) }}
                className="mt-3 text-xs font-mono text-signal-blue hover:text-signal-blue/80"
              >
                clear filters
              </button>
            )}
          </div>
        ) : (
          filteredOptions.map((option) => (
            <OptionRow key={option.option_id} option={option} />
          ))
        )}
      </div>
    </div>
  )
}

function OptionRow({ option }: { option: FeatureOption }) {
  const displayName = option.canonical_name || option.name

  return (
    <Link to={`/options/${option.option_id}`} className="data-row group">
      <div className="w-20 flex-shrink-0">
        <StatusPill status={option.lifecycle_stage} size="sm" showDot={false} />
      </div>

      <div className="flex-1 min-w-0">
        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors truncate block">
          {displayName}
        </span>
      </div>

      <div className="hidden sm:block w-28 flex-shrink-0">
        {option.feature_name && (
          <span className="text-xs font-mono text-zinc-500 truncate block">
            {option.feature_name}
          </span>
        )}
      </div>

      <div className="hidden md:flex items-center gap-3 w-32 flex-shrink-0">
        <DatePill label="B" date={option.beta_date} variant="beta" />
        <DatePill label="P" date={option.production_date} variant="prod" />
      </div>

      <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
    </Link>
  )
}
