import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchApi } from '../api/client'
import type { Feature, FeatureOption, CommunityPost } from '../types'
import { SearchIcon, XMarkIcon, ArrowRightIcon } from './icons'
import StatusPill from './StatusPill'

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

type SearchResult =
  | { type: 'feature'; data: Feature }
  | { type: 'option'; data: FeatureOption }
  | { type: 'content'; data: CommunityPost }

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // Fetch search results
  const { data, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 1000 * 60, // 1 minute
  })

  // Flatten results for keyboard navigation
  const allResults: SearchResult[] = [
    ...(data?.features || []).map(f => ({ type: 'feature' as const, data: f })),
    ...(data?.options || []).map(o => ({ type: 'option' as const, data: o })),
    ...(data?.content || []).map(c => ({ type: 'content' as const, data: c })),
  ]

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0)
  }, [debouncedQuery])

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setDebouncedQuery('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Navigate to result
  const navigateToResult = useCallback((result: SearchResult) => {
    let path = ''
    switch (result.type) {
      case 'feature':
        path = `/features/${result.data.feature_id}`
        break
      case 'option':
        path = `/options/${result.data.option_id}`
        break
      case 'content':
        // Open external content in new tab
        window.open(result.data.url, '_blank')
        onClose()
        return
    }
    navigate(path)
    onClose()
  }, [navigate, onClose])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(i => Math.min(i + 1, allResults.length - 1))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(i => Math.max(i - 1, 0))
          break
        case 'Enter':
          e.preventDefault()
          if (allResults[selectedIndex]) {
            navigateToResult(allResults[selectedIndex])
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, allResults, selectedIndex, navigateToResult, onClose])

  // Scroll selected item into view
  useEffect(() => {
    if (resultsRef.current) {
      const selected = resultsRef.current.querySelector('[data-selected="true"]')
      selected?.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIndex])

  if (!isOpen) return null

  const hasResults = allResults.length > 0
  const showEmptyState = debouncedQuery.length >= 2 && !isLoading && !hasResults

  // Calculate result indices for each section
  const featureStartIndex = 0
  const optionStartIndex = (data?.features?.length || 0)
  const contentStartIndex = optionStartIndex + (data?.options?.length || 0)

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-ink-900/50 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-x-4 top-20 md:inset-x-auto md:left-1/2 md:-translate-x-1/2 md:w-full md:max-w-2xl z-50 animate-slide-up">
        <div className="bg-white rounded-xl shadow-2xl border border-ink-200 overflow-hidden">
          {/* Search input */}
          <div className="relative border-b border-ink-100">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search features, options, content..."
              className="
                w-full pl-12 pr-12 py-4 text-base text-ink-900
                placeholder:text-ink-400 bg-transparent
                focus:outline-none
              "
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Results */}
          <div ref={resultsRef} className="max-h-96 overflow-y-auto">
            {/* Loading state */}
            {isLoading && debouncedQuery.length >= 2 && (
              <div className="p-8 text-center">
                <div className="inline-block w-5 h-5 border-2 border-ink-300 border-t-accent-primary rounded-full animate-spin" />
                <p className="mt-2 text-sm text-ink-500">Searching...</p>
              </div>
            )}

            {/* Empty state */}
            {showEmptyState && (
              <div className="p-8 text-center">
                <p className="text-ink-600 font-medium">No results found</p>
                <p className="mt-1 text-sm text-ink-500">
                  Try a different search term
                </p>
              </div>
            )}

            {/* Initial state */}
            {!debouncedQuery && (
              <div className="p-8 text-center">
                <p className="text-sm text-ink-500">
                  Type at least 2 characters to search
                </p>
                <div className="mt-4 flex items-center justify-center gap-4 text-xs text-ink-400">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-ink-100 rounded text-ink-600 font-mono">↑↓</kbd>
                    Navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-ink-100 rounded text-ink-600 font-mono">↵</kbd>
                    Select
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-ink-100 rounded text-ink-600 font-mono">esc</kbd>
                    Close
                  </span>
                </div>
              </div>
            )}

            {/* Results */}
            {hasResults && !isLoading && (
              <div className="py-2">
                {/* Features */}
                {data?.features && data.features.length > 0 && (
                  <ResultSection title="Features">
                    {data.features.map((feature, i) => {
                      const index = featureStartIndex + i
                      return (
                        <ResultItem
                          key={feature.feature_id}
                          isSelected={selectedIndex === index}
                          onClick={() => navigateToResult({ type: 'feature', data: feature })}
                          onMouseEnter={() => setSelectedIndex(index)}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-ink-900 truncate">{feature.name}</p>
                            {feature.description && (
                              <p className="text-sm text-ink-500 truncate">{feature.description}</p>
                            )}
                          </div>
                          {feature.option_count !== undefined && feature.option_count > 0 && (
                            <span className="text-xs text-ink-500">
                              {feature.option_count} options
                            </span>
                          )}
                        </ResultItem>
                      )
                    })}
                  </ResultSection>
                )}

                {/* Options */}
                {data?.options && data.options.length > 0 && (
                  <ResultSection title="Options">
                    {data.options.map((option, i) => {
                      const index = optionStartIndex + i
                      return (
                        <ResultItem
                          key={option.option_id}
                          isSelected={selectedIndex === index}
                          onClick={() => navigateToResult({ type: 'option', data: option })}
                          onMouseEnter={() => setSelectedIndex(index)}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-ink-900 truncate">
                                {option.canonical_name || option.name}
                              </p>
                              <StatusPill status={option.status} size="sm" showDot={false} />
                            </div>
                            {option.feature_name && (
                              <p className="text-sm text-ink-500 truncate">
                                in {option.feature_name}
                              </p>
                            )}
                          </div>
                        </ResultItem>
                      )
                    })}
                  </ResultSection>
                )}

                {/* Content */}
                {data?.content && data.content.length > 0 && (
                  <ResultSection title="Community">
                    {data.content.map((post, i) => {
                      const index = contentStartIndex + i
                      const isQuestion = post.content_type === 'question'
                      return (
                        <ResultItem
                          key={post.source_id}
                          isSelected={selectedIndex === index}
                          onClick={() => navigateToResult({ type: 'content', data: post })}
                          onMouseEnter={() => setSelectedIndex(index)}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-semibold uppercase tracking-wide ${
                                isQuestion ? 'text-status-optional' : 'text-status-preview'
                              }`}>
                                {isQuestion ? 'Q&A' : 'Blog'}
                              </span>
                              <p className="font-medium text-ink-900 truncate">{post.title}</p>
                            </div>
                          </div>
                          <ArrowRightIcon className="w-4 h-4 text-ink-400 -rotate-45" />
                        </ResultItem>
                      )
                    })}
                  </ResultSection>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function ResultSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-2">
      <h3 className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-ink-500">
        {title}
      </h3>
      {children}
    </div>
  )
}

function ResultItem({
  isSelected,
  onClick,
  onMouseEnter,
  children,
}: {
  isSelected: boolean
  onClick: () => void
  onMouseEnter: () => void
  children: React.ReactNode
}) {
  return (
    <button
      data-selected={isSelected}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      className={`
        w-full px-4 py-2.5 flex items-center gap-3 text-left
        transition-colors
        ${isSelected ? 'bg-ink-100' : 'hover:bg-ink-50'}
      `}
    >
      {children}
    </button>
  )
}
