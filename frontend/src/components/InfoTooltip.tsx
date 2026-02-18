import { useState, useRef, useEffect } from 'react'
import { QuestionMarkCircleIcon, XMarkIcon } from './icons'

interface InfoTooltipProps {
  term: string
  children: React.ReactNode
  className?: string
}

/**
 * Inline educational tooltip for Canvas concepts.
 * Shows a '?' icon that expands to reveal contextual help.
 */
export default function InfoTooltip({ term, children, className = '' }: InfoTooltipProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  return (
    <span ref={containerRef} className={`relative inline-flex items-center ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          inline-flex items-center justify-center w-4 h-4 rounded-full transition-colors
          ${isOpen
            ? 'bg-signal-blue/20 text-signal-blue'
            : 'text-zinc-600 hover:text-zinc-400 hover:bg-surface-3'
          }
        `}
        aria-label={`Learn about ${term}`}
        aria-expanded={isOpen}
      >
        <QuestionMarkCircleIcon className="w-3.5 h-3.5" />
      </button>

      {isOpen && (
        <div className="absolute z-40 left-0 top-full mt-2 w-72 animate-fade-in">
          <div className="bg-surface-3 border border-zinc-700 rounded-lg shadow-elevated p-3.5">
            <div className="flex items-start justify-between gap-2 mb-2">
              <span className="text-xs font-mono font-medium uppercase tracking-widest text-signal-blue">
                {term}
              </span>
              <button
                onClick={() => setIsOpen(false)}
                className="text-zinc-600 hover:text-zinc-400 transition-colors flex-shrink-0"
              >
                <XMarkIcon className="w-3 h-3" />
              </button>
            </div>
            <div className="text-xs text-zinc-400 leading-relaxed space-y-1.5">
              {children}
            </div>
          </div>
        </div>
      )}
    </span>
  )
}

/**
 * Collapsible explainer section for larger educational blocks.
 * Used at the top of pages or sections.
 */
export function InfoBanner({ title, children, storageKey }: { title: string; children: React.ReactNode; storageKey?: string }) {
  const [isDismissed, setIsDismissed] = useState(() => {
    if (storageKey) {
      return localStorage.getItem(`info-dismissed-${storageKey}`) === 'true'
    }
    return false
  })

  const dismiss = () => {
    setIsDismissed(true)
    if (storageKey) {
      localStorage.setItem(`info-dismissed-${storageKey}`, 'true')
    }
  }

  if (isDismissed) {
    return (
      <button
        onClick={() => {
          setIsDismissed(false)
          if (storageKey) localStorage.removeItem(`info-dismissed-${storageKey}`)
        }}
        className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-600 hover:text-zinc-400 transition-colors mb-4"
      >
        <QuestionMarkCircleIcon className="w-3.5 h-3.5" />
        what is this?
      </button>
    )
  }

  return (
    <div className="mb-6 p-4 bg-surface-2 border border-zinc-800/80 rounded-lg animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <QuestionMarkCircleIcon className="w-4 h-4 text-signal-blue flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-signal-blue mb-2">
              {title}
            </h3>
            <div className="text-xs text-zinc-400 leading-relaxed space-y-1.5">
              {children}
            </div>
          </div>
        </div>
        <button
          onClick={dismiss}
          className="text-zinc-600 hover:text-zinc-400 transition-colors flex-shrink-0"
        >
          <XMarkIcon className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}
