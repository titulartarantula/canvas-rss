import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { featuresApi } from '../api/client'
import CategoryFilter from '../components/CategoryFilter'
import FeatureAccordion from '../components/FeatureAccordion'
import { InfoBanner } from '../components/InfoTooltip'
import { SearchIcon, XMarkIcon, AdjustmentsIcon, CogIcon } from '../components/icons'

export default function Registry() {
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

  // Split into features with tracked items vs empty
  const withTracked = filteredFeatures.filter(f => ((f.option_count || 0) + (f.setting_count || 0)) > 0)
  const withoutTracked = filteredFeatures.filter(f => ((f.option_count || 0) + (f.setting_count || 0)) === 0)

  // Totals
  const totalOptions = filteredFeatures.reduce((sum, f) => sum + (f.option_count || 0), 0)
  const totalSettings = filteredFeatures.reduce((sum, f) => sum + (f.setting_count || 0), 0)

  return (
    <div className="animate-fade-in">
      {/* Educational banner */}
      <InfoBanner title="About the Feature Registry" storageKey="registry">
        <p>
          Canvas organizes changes into <strong className="text-zinc-300">features</strong> (like Assignments, Gradebook, etc.).
          Each feature can have two types of tracked changes:
        </p>
        <div className="mt-2 flex flex-col sm:flex-row gap-3">
          <div className="flex items-start gap-2 flex-1">
            <AdjustmentsIcon className="w-3.5 h-3.5 text-signal-violet flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-zinc-300 font-medium">Feature Options</span> are admin toggles that
              you can enable or disable in Canvas Settings.
            </div>
          </div>
          <div className="flex items-start gap-2 flex-1">
            <CogIcon className="w-3.5 h-3.5 text-signal-cyan flex-shrink-0 mt-0.5" />
            <div>
              <span className="text-zinc-300 font-medium">Feature Settings</span> are automatic changes
              (bug fixes, UI improvements) applied by Instructure with no admin action needed.
            </div>
          </div>
        </div>
      </InfoBanner>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-title text-zinc-100">Feature Registry</h1>
          <p className="mt-1 text-xs text-zinc-500 font-mono">
            {isLoading ? '...' : (
              <>
                {filteredFeatures.length} features
                {searchQuery && ` matching "${searchQuery}"`}
                {!searchQuery && totalOptions + totalSettings > 0 && (
                  <span className="text-zinc-600">
                    {' '}&middot; {totalOptions} options, {totalSettings} settings
                  </span>
                )}
              </>
            )}
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
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b border-zinc-800/50 last:border-b-0">
              <div className="w-4"><div className="skeleton h-3.5 w-3.5 rounded" /></div>
              <div className="skeleton h-4 w-40 flex-1" />
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
        <div className="space-y-4">
          {/* Features with tracked options/settings */}
          {withTracked.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-zinc-800/50 flex items-center justify-between">
                <h2 className="text-label uppercase text-zinc-400 font-mono">
                  tracked features ({withTracked.length})
                </h2>
                <div className="flex items-center gap-3 text-xs font-mono text-zinc-500">
                  <span className="inline-flex items-center gap-1">
                    <AdjustmentsIcon className="w-3 h-3 text-signal-violet" /> options
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CogIcon className="w-3 h-3 text-signal-cyan" /> settings
                  </span>
                </div>
              </div>
              {withTracked.map((feature) => (
                <FeatureAccordion key={feature.feature_id} feature={feature} />
              ))}
            </div>
          )}

          {/* Features without tracked items */}
          {withoutTracked.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-4 py-2.5 border-b border-zinc-800/50">
                <h2 className="text-label uppercase text-zinc-400 font-mono">
                  no tracked changes ({withoutTracked.length})
                </h2>
              </div>
              {withoutTracked.map((feature) => (
                <FeatureAccordion key={feature.feature_id} feature={feature} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
