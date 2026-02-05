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
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    }
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const navigatePrevious = () => {
    // Move back ~14 days (Canvas release cycle)
    const baseDate = currentDate ? new Date(currentDate) : new Date()
    baseDate.setDate(baseDate.getDate() - 14)
    onDateChange(baseDate.toISOString().split('T')[0])
  }

  const navigateNext = () => {
    if (isCurrentView) return
    const baseDate = new Date(currentDate!)
    baseDate.setDate(baseDate.getDate() + 14)
    const today = new Date()
    if (baseDate >= today) {
      onDateChange(null) // Return to current
    } else {
      onDateChange(baseDate.toISOString().split('T')[0])
    }
  }

  const goToCurrent = () => {
    onDateChange(null)
  }

  return (
    <div className="flex items-center justify-between py-6">
      {/* Left: Date display with navigation */}
      <div className="flex items-center gap-4">
        <button
          onClick={navigatePrevious}
          className="p-2 rounded-full hover:bg-ink-100 transition-colors text-ink-500 hover:text-ink-700"
          aria-label="Previous release cycle"
        >
          <ChevronLeftIcon className="w-5 h-5" />
        </button>

        <div className="min-w-[280px] text-center">
          <div className={`font-display text-lg text-ink-800 ${isLoading ? 'opacity-50' : ''}`}>
            {formatDisplayDate(currentDate)}
          </div>
        </div>

        <button
          onClick={navigateNext}
          disabled={isCurrentView}
          className={`p-2 rounded-full transition-colors ${
            isCurrentView
              ? 'text-ink-300 cursor-not-allowed'
              : 'hover:bg-ink-100 text-ink-500 hover:text-ink-700'
          }`}
          aria-label="Next release cycle"
        >
          <ChevronRightIcon className="w-5 h-5" />
        </button>
      </div>

      {/* Right: Current badge */}
      <div className="flex items-center gap-3">
        {!isCurrentView && (
          <button
            onClick={goToCurrent}
            className="text-sm text-accent-primary hover:text-accent-primary/80 font-medium transition-colors"
          >
            Jump to current
          </button>
        )}
        {isCurrentView && (
          <span className="date-pill-current date-pill">
            <span className="w-1.5 h-1.5 rounded-full bg-white/80 animate-pulse-soft" />
            Current
          </span>
        )}
      </div>
    </div>
  )
}
