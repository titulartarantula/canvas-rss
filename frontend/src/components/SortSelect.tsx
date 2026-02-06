import { ChevronDownIcon } from './icons'

interface SortSelectProps {
  value: string
  onChange: (sort: string) => void
}

const SORT_OPTIONS = [
  { value: 'updated', label: 'Recently Updated' },
  { value: 'alphabetical', label: 'Alphabetical' },
  { value: 'beta_date', label: 'Beta Date' },
  { value: 'prod_date', label: 'Production Date' },
]

export default function SortSelect({ value, onChange }: SortSelectProps) {
  return (
    <div className="relative inline-flex">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="
          appearance-none bg-transparent border border-ink-200 rounded-lg
          pl-3 pr-9 py-2 text-sm text-ink-700 font-medium
          hover:border-ink-300 hover:bg-ink-50
          focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary
          cursor-pointer transition-colors
        "
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
        <ChevronDownIcon className="w-4 h-4 text-ink-400" />
      </div>
    </div>
  )
}
