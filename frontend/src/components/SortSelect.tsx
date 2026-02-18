import { ChevronDownIcon } from './icons'

interface SortSelectProps {
  value: string
  onChange: (sort: string) => void
}

const SORT_OPTIONS = [
  { value: 'updated', label: 'Updated' },
  { value: 'alphabetical', label: 'A-Z' },
  { value: 'beta_date', label: 'Beta Date' },
  { value: 'prod_date', label: 'Prod Date' },
]

export default function SortSelect({ value, onChange }: SortSelectProps) {
  return (
    <div className="relative inline-flex">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-surface-2 border border-zinc-800 rounded-md
                   pl-2.5 pr-7 py-1 text-xs font-mono text-zinc-400
                   hover:border-zinc-700 focus:outline-none focus:border-zinc-600
                   focus-visible:ring-2 focus-visible:ring-signal-blue/40
                   cursor-pointer transition-colors"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <ChevronDownIcon className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-500 pointer-events-none" />
    </div>
  )
}
