interface StatusFilterProps {
  value: string
  onChange: (status: string) => void
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses', count: null },
  { value: 'pending', label: 'Pending', dotColor: 'bg-status-pending' },
  { value: 'preview', label: 'Preview', dotColor: 'bg-status-preview' },
  { value: 'beta', label: 'Beta', dotColor: 'bg-status-beta' },
  { value: 'optional', label: 'Optional', dotColor: 'bg-status-optional' },
  { value: 'default_on', label: 'Default On', dotColor: 'bg-status-optional' },
  { value: 'released', label: 'Released', dotColor: 'bg-status-released' },
  { value: 'deprecated', label: 'Deprecated', dotColor: 'bg-status-deprecated' },
]

export default function StatusFilter({ value, onChange }: StatusFilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {STATUS_OPTIONS.map((option) => {
        const isSelected = option.value === value
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            className={`
              group relative inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full
              text-xs font-medium tracking-wide transition-all duration-200
              ${isSelected
                ? 'bg-ink-900 text-white shadow-sm'
                : 'bg-ink-100 text-ink-600 hover:bg-ink-200 hover:text-ink-800'
              }
            `}
          >
            {option.dotColor && (
              <span
                className={`
                  w-1.5 h-1.5 rounded-full transition-colors
                  ${isSelected ? 'bg-white' : option.dotColor}
                `}
              />
            )}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

// Compact version for mobile/sidebar
export function StatusFilterCompact({ value, onChange }: StatusFilterProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="
        appearance-none bg-ink-50 border border-ink-200 rounded-lg
        px-3 py-2 pr-8 text-sm text-ink-800 font-medium
        focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary
        cursor-pointer
      "
    >
      {STATUS_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
