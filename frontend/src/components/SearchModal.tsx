import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchApi } from '../api/client'
import type { Feature, FeatureOption, FeatureSetting, CommunityPost } from '../types'
import { SearchIcon, XMarkIcon, ArrowRightIcon } from './icons'
import StatusPill from './StatusPill'

interface SearchModalProps {
  isOpen: boolean
  onClose: () => void
}

type SearchResult =
  | { type: 'feature'; data: Feature }
  | { type: 'option'; data: FeatureOption }
  | { type: 'setting'; data: FeatureSetting }
  | { type: 'content'; data: CommunityPost }

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  const { data, isLoading } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 1000 * 60,
  })

  const allResults: SearchResult[] = [
    ...(data?.features || []).map(f => ({ type: 'feature' as const, data: f })),
    ...(data?.options || []).map(o => ({ type: 'option' as const, data: o })),
    ...(data?.settings || []).map(s => ({ type: 'setting' as const, data: s })),
    ...(data?.content || []).map(c => ({ type: 'content' as const, data: c })),
  ]

  useEffect(() => { setSelectedIndex(0) }, [debouncedQuery])

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setDebouncedQuery('')
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  const navigateToResult = useCallback((result: SearchResult) => {
    let path = ''
    switch (result.type) {
      case 'feature':
        path = `/features/${result.data.feature_id}`
        break
      case 'option':
        path = `/options/${result.data.option_id}`
        break
      case 'setting':
        path = `/settings/${result.data.setting_id}`
        break
      case 'content':
        window.open(result.data.url, '_blank')
        onClose()
        return
    }
    navigate(path)
    onClose()
  }, [navigate, onClose])

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
          if (allResults[selectedIndex]) navigateToResult(allResults[selectedIndex])
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

  useEffect(() => {
    if (resultsRef.current) {
      const selected = resultsRef.current.querySelector('[data-selected="true"]')
      selected?.scrollIntoView({ block: 'nearest' })
    }
  }, [selectedIndex])

  if (!isOpen) return null

  const hasResults = allResults.length > 0
  const showEmptyState = debouncedQuery.length >= 2 && !isLoading && !hasResults

  const featureStartIndex = 0
  const optionStartIndex = (data?.features?.length || 0)
  const settingStartIndex = optionStartIndex + (data?.options?.length || 0)
  const contentStartIndex = settingStartIndex + (data?.settings?.length || 0)

  return (
    <>
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 animate-fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-x-4 top-[15vh] md:inset-x-auto md:left-1/2 md:-translate-x-1/2 md:w-full md:max-w-xl z-50 animate-slide-up">
        <div className="bg-surface-2 rounded-xl border border-zinc-700/80 shadow-elevated overflow-hidden">
          {/* Search input */}
          <div className="relative border-b border-zinc-800">
            <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search features, options, settings..."
              className="
                w-full pl-11 pr-11 py-3.5 text-sm text-zinc-200
                placeholder:text-zinc-600 bg-transparent
                focus:outline-none font-mono
              "
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            )}
          </div>

          <div ref={resultsRef} className="max-h-80 overflow-y-auto">
            {isLoading && debouncedQuery.length >= 2 && (
              <div className="p-6 text-center">
                <div className="inline-block w-4 h-4 border-2 border-zinc-700 border-t-signal-blue rounded-full animate-spin" />
              </div>
            )}

            {showEmptyState && (
              <div className="p-6 text-center">
                <p className="text-zinc-400 text-sm">No results found</p>
                <p className="mt-1 text-xs text-zinc-400">Try a different search term</p>
              </div>
            )}

            {!debouncedQuery && (
              <div className="p-6 text-center">
                <p className="text-xs text-zinc-400 font-mono">type to search</p>
                <div className="mt-3 flex items-center justify-center gap-4 text-xs text-zinc-400 font-mono">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-surface-3 border border-zinc-700 rounded text-zinc-400">↑↓</kbd>
                    nav
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 bg-surface-3 border border-zinc-700 rounded text-zinc-400">↵</kbd>
                    open
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 bg-surface-3 border border-zinc-700 rounded text-zinc-400">esc</kbd>
                    close
                  </span>
                </div>
              </div>
            )}

            {hasResults && !isLoading && (
              <div className="py-1">
                {data?.features && data.features.length > 0 && (
                  <ResultSection title="Features">
                    {data.features.map((feature, i) => (
                      <ResultItem
                        key={feature.feature_id}
                        isSelected={selectedIndex === featureStartIndex + i}
                        onClick={() => navigateToResult({ type: 'feature', data: feature })}
                        onMouseEnter={() => setSelectedIndex(featureStartIndex + i)}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-zinc-200 truncate">{feature.name}</p>
                        </div>
                        {feature.option_count !== undefined && feature.option_count > 0 && (
                          <span className="text-xs font-mono text-zinc-400">
                            {feature.option_count} opts
                          </span>
                        )}
                      </ResultItem>
                    ))}
                  </ResultSection>
                )}

                {data?.options && data.options.length > 0 && (
                  <ResultSection title="Options">
                    {data.options.map((option, i) => (
                      <ResultItem
                        key={option.option_id}
                        isSelected={selectedIndex === optionStartIndex + i}
                        onClick={() => navigateToResult({ type: 'option', data: option })}
                        onMouseEnter={() => setSelectedIndex(optionStartIndex + i)}
                      >
                        <div className="flex-1 min-w-0 flex items-center gap-2">
                          <p className="text-sm text-zinc-200 truncate">{option.canonical_name || option.name}</p>
                          <StatusPill status={option.lifecycle_stage} size="sm" showDot={false} />
                        </div>
                      </ResultItem>
                    ))}
                  </ResultSection>
                )}

                {data?.settings && data.settings.length > 0 && (
                  <ResultSection title="Settings">
                    {data.settings.map((setting, i) => (
                      <ResultItem
                        key={setting.setting_id}
                        isSelected={selectedIndex === settingStartIndex + i}
                        onClick={() => navigateToResult({ type: 'setting', data: setting })}
                        onMouseEnter={() => setSelectedIndex(settingStartIndex + i)}
                      >
                        <div className="flex-1 min-w-0 flex items-center gap-2">
                          <p className="text-sm text-zinc-200 truncate">{setting.name}</p>
                          <StatusPill status={setting.status} size="sm" showDot={false} />
                        </div>
                      </ResultItem>
                    ))}
                  </ResultSection>
                )}

                {data?.content && data.content.length > 0 && (
                  <ResultSection title="Community">
                    {data.content.map((post, i) => (
                      <ResultItem
                        key={post.source_id}
                        isSelected={selectedIndex === contentStartIndex + i}
                        onClick={() => navigateToResult({ type: 'content', data: post })}
                        onMouseEnter={() => setSelectedIndex(contentStartIndex + i)}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-zinc-200 truncate">{post.title}</p>
                        </div>
                        <ArrowRightIcon className="w-3.5 h-3.5 text-zinc-500 -rotate-45" />
                      </ResultItem>
                    ))}
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
    <div className="py-1">
      <h3 className="px-4 py-1.5 text-xs font-mono font-medium uppercase tracking-widest text-zinc-400">
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
        w-full px-4 py-2 flex items-center gap-3 text-left transition-colors
        ${isSelected ? 'bg-surface-3' : 'hover:bg-surface-3/50'}
      `}
    >
      {children}
    </button>
  )
}
