import { ChevronLeftIcon, ChevronRightIcon } from './icons'

interface DateNavigatorProps {
  currentDate: string | null
  onDateChange: (date: string | null) => void
  isLoading?: boolean
}

export default function DateNavigator({ currentDate, onDateChange, isLoading }: DateNavigatorProps) {
  const isCurrentView = !currentDate

  const formatDisplayDate = (dateStr: string | null) => {
    if (!dateStr) {
      return new Date().toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    }
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
    const d = match
      ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
      : new Date(dateStr)
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const parseLocalDate = (dateStr: string): Date => {
    const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})/)
    return match
      ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
      : new Date(dateStr)
  }

  const toDateString = (d: Date): string => {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  const navigatePrevious = () => {
    const baseDate = currentDate ? parseLocalDate(currentDate) : new Date()
    baseDate.setDate(baseDate.getDate() - 14)
    onDateChange(toDateString(baseDate))
  }

  const navigateNext = () => {
    if (isCurrentView) return
    const baseDate = parseLocalDate(currentDate!)
    baseDate.setDate(baseDate.getDate() + 14)
    const today = new Date()
    if (baseDate >= today) {
      onDateChange(null)
    } else {
      onDateChange(toDateString(baseDate))
    }
  }

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <button
          onClick={navigatePrevious}
          className="p-1.5 rounded-md hover:bg-surface-3 transition-colors text-zinc-500 hover:text-zinc-300"
          aria-label="Previous release cycle"
        >
          <ChevronLeftIcon className="w-4 h-4" />
        </button>

        <span className={`font-mono text-sm text-zinc-300 tabular-nums ${isLoading ? 'opacity-50' : ''}`}>
          {formatDisplayDate(currentDate)}
        </span>

        <button
          onClick={navigateNext}
          disabled={isCurrentView}
          className={`p-1.5 rounded-md transition-colors ${
            isCurrentView
              ? 'text-zinc-700 cursor-not-allowed'
              : 'hover:bg-surface-3 text-zinc-500 hover:text-zinc-300'
          }`}
          aria-label="Next release cycle"
        >
          <ChevronRightIcon className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center gap-2">
        {!isCurrentView && (
          <button
            onClick={() => onDateChange(null)}
            className="text-xs font-mono text-signal-blue hover:text-signal-blue/80 transition-colors"
          >
            jump to current
          </button>
        )}
        {isCurrentView && (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-signal-green/10 text-signal-green text-xs font-mono font-medium">
            <span className="w-1 h-1 rounded-full bg-signal-green animate-pulse-dot" />
            LIVE
          </span>
        )}
      </div>
    </div>
  )
}
