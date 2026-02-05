import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { featuresApi } from '../api/client'
import FeatureCard, { FeatureCardSkeleton } from '../components/FeatureCard'
import CategoryFilter from '../components/CategoryFilter'
import { SearchIcon, XMarkIcon } from '../components/icons'

export default function Features() {
  const [searchParams, setSearchParams] = useSearchParams()
  const categoryParam = searchParams.get('category') || ''
  const [searchQuery, setSearchQuery] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['features', categoryParam],
    queryFn: () => featuresApi.list(categoryParam || undefined),
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const handleCategoryChange = (category: string) => {
    if (category) {
      setSearchParams({ category })
    } else {
      setSearchParams({})
    }
  }

  // Filter features by search query (client-side)
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

  const featureCount = filteredFeatures.length
  const totalCount = data?.features?.length || 0

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="font-display text-display-sm font-semibold text-ink-900">
          Features
        </h1>
        <p className="mt-2 text-ink-600 max-w-2xl">
          Explore Canvas LMS features and their associated feature options. Click on a feature to see its deployment status and history.
        </p>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        {/* Search input */}
        <div className="relative flex-1 max-w-md">
          <SearchIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400" />
          <input
            type="text"
            placeholder="Search features..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm border border-ink-200 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary
                       placeholder:text-ink-400 transition-all duration-150"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600"
            >
              <span className="sr-only">Clear</span>
              <XMarkIcon className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Category filter */}
        <CategoryFilter
          value={categoryParam}
          onChange={handleCategoryChange}
        />
      </div>

      {/* Results count */}
      <div className="flex items-center justify-between mb-6">
        <p className="text-sm text-ink-600">
          {isLoading ? (
            <span className="skeleton inline-block h-4 w-32" />
          ) : searchQuery ? (
            <>
              <span className="font-medium text-ink-800">{featureCount}</span>
              {' '}of {totalCount} features
            </>
          ) : (
            <>
              <span className="font-medium text-ink-800">{featureCount}</span>
              {' '}{featureCount === 1 ? 'feature' : 'features'}
            </>
          )}
        </p>
      </div>

      {/* Error state */}
      {isError && (
        <div className="card p-8 text-center">
          <p className="text-status-deprecated font-medium">Failed to load features</p>
          <p className="mt-2 text-sm text-ink-500">
            {error instanceof Error ? error.message : 'Please try again later'}
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <FeatureCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && filteredFeatures.length === 0 && (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-ink-100 flex items-center justify-center">
            <SearchIcon className="w-6 h-6 text-ink-400" />
          </div>
          <p className="text-ink-700 font-medium">No features found</p>
          <p className="mt-1 text-sm text-ink-500">
            {searchQuery
              ? `No features match "${searchQuery}"`
              : 'Try selecting a different category'}
          </p>
          {(searchQuery || categoryParam) && (
            <button
              onClick={() => {
                setSearchQuery('')
                setSearchParams({})
              }}
              className="mt-4 text-sm text-accent-primary hover:text-accent-primary/80 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Features grid */}
      {!isLoading && !isError && filteredFeatures.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredFeatures.map((feature, index) => (
            <div key={feature.feature_id} className="animate-slide-up" style={{ animationDelay: `${index * 30}ms` }}>
              <FeatureCard feature={feature} index={index} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
