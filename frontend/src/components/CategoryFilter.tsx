import { useState, useRef, useEffect } from 'react'

export interface Category {
  id: string
  label: string
  description?: string
}

export const FEATURE_CATEGORIES: Category[] = [
  { id: '', label: 'All Categories', description: 'View all features' },
  { id: 'core', label: 'Core Course', description: 'Assignments, Modules, Pages, Files' },
  { id: 'grading', label: 'Grading & Assessment', description: 'Gradebook, SpeedGrader, Rubrics' },
  { id: 'quizzes', label: 'Quizzes', description: 'Classic Quizzes, New Quizzes' },
  { id: 'collaboration', label: 'Collaboration', description: 'Groups, Conferences, Chat' },
  { id: 'communication', label: 'Communication', description: 'Inbox, Calendar, Notifications' },
  { id: 'ui', label: 'User Interface', description: 'Dashboard, Navigation, Editor' },
  { id: 'portfolio', label: 'ePortfolios', description: 'Student portfolios' },
  { id: 'analytics', label: 'Analytics', description: 'Canvas Analytics, Data Services' },
  { id: 'addons', label: 'Add-on Products', description: 'Studio, Catalog, Commons' },
  { id: 'mobile', label: 'Mobile', description: 'Canvas Mobile apps' },
  { id: 'admin', label: 'Administration', description: 'Import, SIS, Settings, API' },
]

interface CategoryFilterProps {
  value: string
  onChange: (category: string) => void
}

export default function CategoryFilter({ value, onChange }: CategoryFilterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const selectedCategory = FEATURE_CATEGORIES.find(c => c.id === value) || FEATURE_CATEGORIES[0]

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close on escape
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
          flex items-center justify-between gap-3 w-full min-w-[200px]
          px-4 py-2.5 rounded-lg border text-left
          transition-all duration-150
          ${isOpen
            ? 'border-accent-primary ring-2 ring-accent-primary/20 bg-white'
            : 'border-ink-200 hover:border-ink-300 bg-white'
          }
        `}
      >
        <div className="flex-1 min-w-0">
          <span className="block text-sm font-medium text-ink-800 truncate">
            {selectedCategory.label}
          </span>
        </div>
        <ChevronDownIcon
          className={`w-4 h-4 text-ink-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-72 py-2 bg-white rounded-xl border border-ink-200 shadow-elevated animate-fade-in">
          <div className="px-3 pb-2 mb-2 border-b border-ink-100">
            <span className="text-[10px] font-medium uppercase tracking-wider text-ink-500">
              Filter by Category
            </span>
          </div>
          <div className="max-h-[320px] overflow-y-auto">
            {FEATURE_CATEGORIES.map((category) => (
              <button
                key={category.id}
                onClick={() => {
                  onChange(category.id)
                  setIsOpen(false)
                }}
                className={`
                  w-full px-3 py-2.5 text-left transition-colors
                  ${value === category.id
                    ? 'bg-accent-primary/5'
                    : 'hover:bg-ink-50'
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  {value === category.id && (
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
                  )}
                  <span className={`
                    text-sm font-medium
                    ${value === category.id ? 'text-accent-primary' : 'text-ink-800'}
                  `}>
                    {category.label}
                  </span>
                </div>
                {category.description && (
                  <p className={`
                    mt-0.5 text-xs leading-snug
                    ${value === category.id ? 'text-accent-primary/70' : 'text-ink-500'}
                    ${value === category.id ? 'ml-3.5' : ''}
                  `}>
                    {category.description}
                  </p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Simple chevron icon component
function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
    </svg>
  )
}
