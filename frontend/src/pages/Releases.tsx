import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { releasesApi } from '../api/client'
import type { Release } from '../types'
import ReleaseRow, { ReleaseRowSkeleton } from '../components/ReleaseRow'
import { SearchIcon, XMarkIcon, ArchiveIcon, ChevronDownIcon } from '../components/icons'

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'release_note', label: 'Release Notes' },
  { value: 'deploy_note', label: 'Deploy Notes' },
]

// Generate year options from 2020 to current year
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

  // State from URL params
  const type = searchParams.get('type') || ''
  const year = searchParams.get('year') || ''
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '')
  const [debouncedSearch, setDebouncedSearch] = useState(searchQuery)

  // Debounce search
  useMemo(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery)
      if (searchQuery) {
        setSearchParams(prev => {
          prev.set('search', searchQuery)
          return prev
        })
      } else {
        setSearchParams(prev => {
          prev.delete('search')
          return prev
        })
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, setSearchParams])

  // Fetch releases
  const { data, isLoading, isError } = useQuery({
    queryKey: ['releases', { type, year, search: debouncedSearch }],
    queryFn: () => releasesApi.list({
      type: type || undefined,
      year: year ? parseInt(year) : undefined,
      search: debouncedSearch || undefined,
    }),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Update URL params
  const updateParams = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams)
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value)
      } else {
        newParams.delete(key)
      }
    })
    setSearchParams(newParams)
  }

  // Group releases by month
  const groupedReleases = useMemo(() => {
    if (!data?.releases) return []

    const groups: { month: string; monthKey: string; releases: Release[] }[] = []
    const monthMap = new Map<string, Release[]>()

    data.releases.forEach(release => {
      const date = new Date(release.first_posted)
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
      {/* Header */}
      <header>
        <h1 className="font-display text-display font-semibold text-ink-900">
          Release Archive
        </h1>
        <p className="mt-2 text-ink-600 max-w-2xl">
          Browse the complete history of Canvas release notes and deployment updates.
        </p>
      </header>

      {/* Toolbar */}
      <div className="mt-8 space-y-4">
        {/* Search bar */}
        <div className="relative max-w-md">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <SearchIcon className="w-4 h-4 text-ink-400" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search releases..."
            className="
              w-full pl-10 pr-10 py-2.5 bg-white border border-ink-200 rounded-lg
              text-sm text-ink-800 placeholder:text-ink-400
              focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary
              transition-colors
            "
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Type filter pills */}
          <div className="flex items-center gap-1.5">
            {TYPE_OPTIONS.map((option) => {
              const isSelected = option.value === type
              return (
                <button
                  key={option.value}
                  onClick={() => updateParams({ type: option.value })}
                  className={`
                    px-3 py-1.5 rounded-full text-xs font-medium tracking-wide
                    transition-all duration-200
                    ${isSelected
                      ? 'bg-ink-900 text-white shadow-sm'
                      : 'bg-ink-100 text-ink-600 hover:bg-ink-200 hover:text-ink-800'
                    }
                  `}
                >
                  {option.label}
                </button>
              )
            })}
          </div>

          {/* Year dropdown */}
          <div className="relative">
            <select
              value={year}
              onChange={(e) => updateParams({ year: e.target.value })}
              className="
                appearance-none bg-transparent border border-ink-200 rounded-lg
                pl-3 pr-9 py-1.5 text-xs font-medium text-ink-700
                hover:border-ink-300 hover:bg-ink-50
                focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary
                cursor-pointer transition-colors
              "
            >
              {YEAR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              <ChevronDownIcon className="w-3.5 h-3.5 text-ink-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Results count */}
      <div className="mt-6 flex items-center gap-2 text-sm text-ink-500">
        {isLoading ? (
          <span className="skeleton h-4 w-32" />
        ) : (
          <>
            <ArchiveIcon className="w-4 h-4" />
            <span>
              <span className="font-medium text-ink-700">{totalCount}</span>
              {' '}{totalCount === 1 ? 'release' : 'releases'}
            </span>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="mt-4 border-t border-ink-200" />

      {/* Releases list */}
      <div className="mt-6">
        {isLoading ? (
          <div className="space-y-4">
            <div className="skeleton h-6 w-40 mb-4" />
            {Array.from({ length: 5 }).map((_, i) => (
              <ReleaseRowSkeleton key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="card p-12 text-center">
            <p className="text-status-deprecated font-medium">Failed to load releases</p>
            <p className="mt-2 text-sm text-ink-500">
              There was an error loading the release archive. Please try again.
            </p>
          </div>
        ) : groupedReleases.length === 0 ? (
          <div className="card p-12 text-center">
            <ArchiveIcon className="w-10 h-10 mx-auto text-ink-300" />
            <p className="mt-4 font-medium text-ink-700">No releases found</p>
            <p className="mt-1 text-sm text-ink-500">
              {searchQuery || type || year
                ? 'Try adjusting your search or filters'
                : 'No releases have been archived yet'}
            </p>
            {(type || year || searchQuery) && (
              <button
                onClick={() => {
                  setSearchQuery('')
                  updateParams({ type: '', year: '' })
                }}
                className="mt-4 text-sm text-accent-primary hover:text-accent-primary/80 font-medium"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-8">
            {groupedReleases.map((group) => (
              <section key={group.monthKey}>
                {/* Month header */}
                <h3 className="font-display text-sm font-semibold text-ink-500 uppercase tracking-wider mb-2">
                  {group.month}
                </h3>

                {/* Releases in this month */}
                <div className="divide-y divide-ink-100">
                  {group.releases.map((release, index) => (
                    <ReleaseRow key={release.source_id} release={release} index={index} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
