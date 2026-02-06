import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { optionsApi } from '../api/client'
import StatusFilter from '../components/StatusFilter'
import SortSelect from '../components/SortSelect'
import OptionRow, { OptionRowSkeleton } from '../components/OptionRow'
import { AdjustmentsIcon, SearchIcon, XMarkIcon } from '../components/icons'

export default function Options() {
  const [searchParams, setSearchParams] = useSearchParams()

  // State from URL params
  const status = searchParams.get('status') || ''
  const sort = searchParams.get('sort') || 'updated'
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch options
  const { data, isLoading, isError } = useQuery({
    queryKey: ['options', { status, sort }],
    queryFn: () => optionsApi.list({ status: status || undefined, sort }),
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

  // Filter options by search query (client-side)
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

  // Stats for header
  const totalCount = data?.options?.length || 0
  const filteredCount = filteredOptions.length

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <header>
        <h1 className="font-display text-display font-semibold text-ink-900">
          Feature Options
        </h1>
        <p className="mt-2 text-ink-600 max-w-2xl">
          Browse all Canvas feature flags and configuration options. Filter by status or search to find specific options.
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
            placeholder="Search options..."
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

        {/* Filter and sort row */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <StatusFilter
            value={status}
            onChange={(newStatus) => updateParams({ status: newStatus })}
          />

          <div className="flex items-center gap-3">
            <span className="text-sm text-ink-500">Sort by</span>
            <SortSelect
              value={sort}
              onChange={(newSort) => updateParams({ sort: newSort })}
            />
          </div>
        </div>
      </div>

      {/* Results count */}
      <div className="mt-6 flex items-center gap-2 text-sm text-ink-500">
        {isLoading ? (
          <span className="skeleton h-4 w-32" />
        ) : (
          <>
            <AdjustmentsIcon className="w-4 h-4" />
            <span>
              {searchQuery ? (
                <>
                  <span className="font-medium text-ink-700">{filteredCount}</span>
                  {' '}of {totalCount} options
                </>
              ) : (
                <>
                  <span className="font-medium text-ink-700">{totalCount}</span>
                  {' '}{totalCount === 1 ? 'option' : 'options'}
                </>
              )}
            </span>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="mt-4 border-t border-ink-200" />

      {/* Options list */}
      <div className="mt-6">
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <OptionRowSkeleton key={i} />
            ))}
          </div>
        ) : isError ? (
          <div className="card p-12 text-center">
            <p className="text-status-deprecated font-medium">Failed to load options</p>
            <p className="mt-2 text-sm text-ink-500">
              There was an error loading the feature options. Please try again.
            </p>
          </div>
        ) : filteredOptions.length === 0 ? (
          <div className="card p-12 text-center">
            <AdjustmentsIcon className="w-10 h-10 mx-auto text-ink-300" />
            <p className="mt-4 font-medium text-ink-700">No options found</p>
            <p className="mt-1 text-sm text-ink-500">
              {searchQuery
                ? `No options match "${searchQuery}"`
                : 'No options match the selected filters'}
            </p>
            {(status || searchQuery) && (
              <button
                onClick={() => {
                  setSearchQuery('')
                  updateParams({ status: '' })
                }}
                className="mt-4 text-sm text-accent-primary hover:text-accent-primary/80 font-medium"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredOptions.map((option, index) => (
              <OptionRow key={option.option_id} option={option} index={index} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
