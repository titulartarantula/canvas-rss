import { useState, useRef, useEffect } from 'react'

export interface Category {
  id: string
  label: string
  description?: string
}

export const FEATURE_CATEGORIES: Category[] = [
  { id: '', label: 'All Categories' },
  { id: 'core', label: 'Core Course' },
  { id: 'grading', label: 'Grading & Assessment' },
  { id: 'quizzes', label: 'Quizzes' },
  { id: 'collaboration', label: 'Collaboration' },
  { id: 'communication', label: 'Communication' },
  { id: 'ui', label: 'User Interface' },
  { id: 'portfolio', label: 'ePortfolios' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'addons', label: 'Add-on Products' },
  { id: 'mobile', label: 'Mobile' },
  { id: 'admin', label: 'Administration' },
]

interface CategoryFilterProps {
  value: string
  onChange: (category: string) => void
}

export default function CategoryFilter({ value, onChange }: CategoryFilterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const selectedCategory = FEATURE_CATEGORIES.find(c => c.id === value) || FEATURE_CATEGORIES[0]

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [])

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center justify-between gap-2 min-w-[160px]
          px-3 py-2 rounded-md border text-left text-sm font-mono transition-colors
          ${isOpen
            ? 'border-zinc-600 bg-surface-3 text-zinc-300'
            : 'border-zinc-800 bg-surface-2 text-zinc-400 hover:border-zinc-700'
          }
        `}
      >
        <span className="truncate text-[13px]">{selectedCategory.label}</span>
        <ChevronIcon className={`w-3 h-3 text-zinc-600 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-56 py-1 bg-surface-2 rounded-lg border border-zinc-700 shadow-elevated animate-fade-in">
          {FEATURE_CATEGORIES.map((category) => (
            <button
              key={category.id}
              onClick={() => { onChange(category.id); setIsOpen(false) }}
              className={`
                w-full px-3 py-2 text-left text-[13px] font-mono transition-colors
                ${value === category.id
                  ? 'bg-surface-3 text-signal-blue'
                  : 'text-zinc-400 hover:bg-surface-3 hover:text-zinc-200'
                }
              `}
            >
              {category.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  )
}
