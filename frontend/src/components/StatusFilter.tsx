interface StatusFilterProps {
  value: string
  onChange: (status: string) => void
}

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending', color: 'bg-status-pending' },
  { value: 'preview', label: 'Preview', color: 'bg-status-preview' },
  { value: 'beta', label: 'Beta', color: 'bg-status-beta' },
  { value: 'optional', label: 'Optional', color: 'bg-status-optional' },
  { value: 'default_on', label: 'Default On', color: 'bg-status-optional' },
  { value: 'released', label: 'Released', color: 'bg-status-released' },
  { value: 'delayed', label: 'Delayed', color: 'bg-amber-400' },
  { value: 'deprecated', label: 'Deprecated', color: 'bg-status-deprecated' },
]

export default function StatusFilter({ value, onChange }: StatusFilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-0.5">
      {STATUS_OPTIONS.map((option) => {
        const isSelected = option.value === value
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            className={`
              inline-flex items-center gap-1 px-2.5 py-1 rounded-md
              text-xs font-mono font-medium transition-colors
              ${isSelected
                ? 'bg-zinc-700 text-white'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-surface-3'
              }
            `}
          >
            {option.color && (
              <span className={`w-1 h-1 rounded-full ${isSelected ? 'bg-white' : option.color}`} />
            )}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}

export function StatusFilterCompact({ value, onChange }: StatusFilterProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="appearance-none bg-surface-2 border border-zinc-800 rounded-md
                 px-2.5 pr-7 py-1.5 text-xs font-mono text-zinc-400
                 focus:outline-none focus:border-zinc-600 focus-visible:ring-2 focus-visible:ring-signal-blue/40 cursor-pointer"
    >
      {STATUS_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  )
}
