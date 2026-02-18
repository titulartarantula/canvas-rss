import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { releasesApi } from '../api/client'
import type { Release } from '../types'
import { SearchIcon, XMarkIcon, ArrowRightIcon, DocumentIcon, ChevronDownIcon } from '../components/icons'

const TYPE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'release_note', label: 'Release' },
  { value: 'deploy_note', label: 'Deploy' },
]

const currentYear = new Date().getFullYear()
const YEAR_OPTIONS = [
  { value: '', label: 'All Years' },
  ...Array.from({ length: currentYear - 2019 }, (_, i) => ({
    value: String(currentYear - i),
    label: String(currentYear - i),
  })),
]

export default function Releases() {
  const [searchParams, setSearchParams] = useSearchParams()
  const type = searchParams.get('type') || ''
  const year = searchParams.get('year') || ''
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [debouncedSearch, setDebouncedSearch] = useState(searchQuery)

  useMemo(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      if (searchQuery) {
        setSearchParams(prev => { prev.set('search', searchQuery); return prev })
      } else {
        setSearchParams(prev => { prev.delete('search'); return prev })
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, setSearchParams])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['releases', { type, year, search: debouncedSearch }],
    queryFn: () => releasesApi.list({
      type: type || undefined,
      year: year ? parseInt(year) : undefined,
      search: debouncedSearch || undefined,
    }),
    staleTime: 1000 * 60 * 5,
  })

  const updateParams = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value) { newParams.set(key, value) } else { newParams.delete(key) }
    })
    setSearchParams(newParams)
  }

  const groupedReleases = useMemo(() => {
    if (!data?.releases) return []
    const groups: { month: string; monthKey: string; releases: Release[] }[] = []
    const monthMap = new Map<string, Release[]>()
    data.releases.forEach(release => {
      const dateStr = release.production_date || release.published_date || ''
      const dateMatch = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
      const date = dateMatch
        ? new Date(Number(dateMatch[1]), Number(dateMatch[2]) - 1, Number(dateMatch[3]))
        : new Date(dateStr)
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      const monthLabel = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
      if (!monthMap.has(monthKey)) {
        monthMap.set(monthKey, [])
        groups.push({ month: monthLabel, monthKey, releases: monthMap.get(monthKey)! })
      }
      monthMap.get(monthKey)!.push(release)
    })
    return groups
  }, [data?.releases])

  const totalCount = data?.releases?.length || 0

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Release History</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : `${totalCount} releases`}
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
            placeholder="Search releases..."
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

        <div className="flex flex-wrap items-center gap-2">
          {/* Type filter */}
          <div className="flex items-center gap-0.5">
            {TYPE_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => updateParams({ type: option.value })}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium transition-colors ${
                  option.value === type
                    ? 'bg-zinc-700 text-white'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-surface-3'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Year dropdown */}
          <div className="relative">
            <select
              value={year}
              onChange={(e) => updateParams({ year: e.target.value })}
              className="appearance-none bg-surface-2 border border-zinc-800 rounded-md
                         pl-2.5 pr-7 py-1 text-xs font-mono text-zinc-400
                         hover:border-zinc-700 focus:outline-none focus:border-zinc-600
                         focus-visible:ring-2 focus-visible:ring-signal-blue/40
                         cursor-pointer transition-colors"
            >
              {YEAR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
            <ChevronDownIcon className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-600 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Releases */}
      {isLoading ? (
        <div className="card overflow-hidden">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="data-row">
              <div className="w-14"><div className="skeleton h-4 w-12" /></div>
              <div className="w-16"><div className="skeleton h-4 w-14 rounded" /></div>
              <div className="flex-1"><div className="skeleton h-4 w-64" /></div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="card p-8 text-center">
          <p className="text-signal-red text-sm">Failed to load releases</p>
        </div>
      ) : groupedReleases.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="text-sm text-zinc-500">No releases found</p>
          {(type || year || searchQuery) && (
            <button
              onClick={() => { setSearchQuery(''); updateParams({ type: '', year: '' }) }}
              className="mt-3 text-xs font-mono text-signal-blue hover:text-signal-blue/80"
            >
              clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {groupedReleases.map((group) => (
            <div key={group.monthKey}>
              <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-400 mb-2 px-1">
                {group.month}
              </h3>
              <div className="card overflow-hidden">
                {group.releases.map((release) => (
                  <ReleaseRow key={release.source_id} release={release} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ReleaseRow({ release }: { release: Release }) {
  const isDeployNote = release.content_type === 'deploy_note'
  const typeLabel = isDeployNote ? 'Deploy' : 'Release'
  const typeColor = isDeployNote ? 'text-status-optional bg-status-optional/15' : 'text-status-beta bg-status-beta/15'

  const dateStr = release.production_date || release.published_date || ''
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
  const date = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(dateStr)
  const formattedDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

  return (
    <Link to={`/releases/${release.source_id}`} className="data-row group">
      <div className="w-14 flex-shrink-0">
        <span className="text-xs font-mono text-zinc-400">{formattedDate}</span>
      </div>

      <div className="w-16 flex-shrink-0">
        <span className={`pill ${typeColor}`}>{typeLabel}</span>
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-300 group-hover:text-white transition-colors truncate">
          {release.title}
        </p>
      </div>

      {release.announcement_count !== undefined && release.announcement_count > 0 && (
        <div className="flex-shrink-0 flex items-center gap-1 text-xs font-mono text-zinc-400 hidden sm:flex">
          <DocumentIcon className="w-3 h-3" />
          {release.announcement_count}
        </div>
      )}

      <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
    </Link>
  )
}
