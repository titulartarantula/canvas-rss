import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { featuresApi } from '../api/client'
import type { Feature } from '../types'
import CategoryFilter from '../components/CategoryFilter'
import { SearchIcon, XMarkIcon, ArrowRightIcon } from '../components/icons'

export default function Features() {
  const [searchParams, setSearchParams] = useSearchParams()
  const categoryParam = searchParams.get('category') || ''
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['features', categoryParam],
    queryFn: () => featuresApi.list(categoryParam || undefined),
    staleTime: 1000 * 60 * 5,
  })

  const handleCategoryChange = (category: string) => {
    if (category) {
      setSearchParams({ category })
    } else {
      setSearchParams({})
    }
  }

  const filteredFeatures = useMemo(() => {
    if (!data?.features) return []
    if (!searchQuery.trim()) return data.features
    const query = searchQuery.toLowerCase()
    return data.features.filter(
      feature =>
        feature.name.toLowerCase().includes(query) ||
        feature.description?.toLowerCase().includes(query)
    )
  }, [data?.features, searchQuery])

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Features</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : `${filteredFeatures.length} features`}
            {searchQuery && ` matching "${searchQuery}"`}
          </p>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-600" />
          <input
            type="text"
            placeholder="Search features..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
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
        <CategoryFilter value={categoryParam} onChange={handleCategoryChange} />
      </div>

      {isError && (
        <div className="card p-6 text-center">
          <p className="text-signal-red text-sm">Failed to load features</p>
          <p className="mt-1 text-xs text-zinc-500">{error instanceof Error ? error.message : 'Please try again'}</p>
        </div>
      )}

      {isLoading && (
        <div className="card overflow-hidden">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="data-row">
              <div className="skeleton h-4 w-40" />
              <div className="flex-1" />
              <div className="skeleton h-4 w-12" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && !isError && filteredFeatures.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-sm text-zinc-400">No features found</p>
          {(searchQuery || categoryParam) && (
            <button
              onClick={() => { setSearchQuery(''); setSearchParams({}) }}
              className="mt-3 text-xs font-mono text-signal-blue hover:text-signal-blue/80"
            >
              clear filters
            </button>
          )}
        </div>
      )}

      {!isLoading && !isError && filteredFeatures.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 py-2.5 border-b border-zinc-800/50">
            <h2 className="text-label uppercase text-zinc-400 font-mono">
              all features ({filteredFeatures.length})
            </h2>
          </div>
          {filteredFeatures.map((feature) => (
            <FeatureRow key={feature.feature_id} feature={feature} />
          ))}
        </div>
      )}
    </div>
  )
}

function FeatureRow({ feature }: { feature: Feature }) {
  const optionCount = feature.option_count || 0
  const statusSummary = feature.status_summary || ''

  return (
    <Link
      to={`/features/${feature.feature_id}`}
      className="data-row group"
    >
      {/* Name */}
      <div className="flex-1 min-w-0">
        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors">
          {feature.name}
        </span>
      </div>

      {/* Status summary */}
      {statusSummary && (
        <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
          {statusSummary.split(',').map((part, idx) => (
            <span key={idx} className={`text-xs font-mono ${getStatusTextColor(part.trim())}`}>
              {part.trim()}
            </span>
          ))}
        </div>
      )}

      {/* Option count */}
      <div className="w-16 flex-shrink-0 text-right">
        {optionCount > 0 ? (
          <span className="text-xs font-mono text-zinc-400">{optionCount} opts</span>
        ) : (
          <span className="text-xs font-mono text-zinc-500">--</span>
        )}
      </div>

      <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors flex-shrink-0" />
    </Link>
  )
}

function getStatusTextColor(text: string): string {
  if (text.includes('preview')) return 'text-status-preview'
  if (text.includes('pending')) return 'text-status-pending'
  if (text.includes('optional')) return 'text-status-optional'
  if (text.includes('beta')) return 'text-status-beta'
  if (text.includes('stable') || text.includes('released')) return 'text-status-released'
  return 'text-zinc-500'
}
