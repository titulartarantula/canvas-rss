interface DeploymentTimelineProps {
  status: string
  firstSeen: string | null
  betaDate: string | null
  productionDate: string | null
  deprecationDate: string | null
}

type Stage = {
  key: string
  label: string
  date: string | null
  isActive: boolean
  isComplete: boolean
  isCurrent: boolean
}

export default function DeploymentTimeline({
  status,
  firstSeen,
  betaDate,
  productionDate,
  deprecationDate,
}: DeploymentTimelineProps) {
  const normalizedStatus = status?.toLowerCase().replace(/\s+/g, '_') || 'pending'
  const today = new Date().toISOString().split('T')[0] // YYYY-MM-DD for lexicographic comparison

  // Build stages based on available dates and current status
  const stages: Stage[] = []

  // Announced stage
  stages.push({
    key: 'announced',
    label: 'Announced',
    date: firstSeen,
    isActive: true,
    isComplete: !!firstSeen,
    isCurrent: normalizedStatus === 'pending',
  })

  // Beta stage
  stages.push({
    key: 'beta',
    label: 'Beta',
    date: betaDate,
    isActive: !!betaDate || normalizedStatus === 'beta',
    isComplete: !!betaDate && betaDate <= today && normalizedStatus !== 'beta',
    isCurrent: normalizedStatus === 'beta',
  })

  // Production/Optional stage
  const isProdPhase = ['optional', 'default_on', 'preview'].includes(normalizedStatus)
  stages.push({
    key: 'production',
    label: productionDate ? 'Production' : 'Optional',
    date: productionDate,
    isActive: !!productionDate || isProdPhase,
    isComplete: !!productionDate && productionDate <= today && !isProdPhase,
    isCurrent: isProdPhase,
  })

  // Released stage
  stages.push({
    key: 'released',
    label: 'Released',
    date: normalizedStatus === 'released' ? productionDate : null,
    isActive: normalizedStatus === 'released',
    isComplete: normalizedStatus === 'released',
    isCurrent: normalizedStatus === 'released',
  })

  // Deprecated (only show if deprecated)
  if (deprecationDate || normalizedStatus === 'deprecated') {
    stages.push({
      key: 'deprecated',
      label: 'Deprecated',
      date: deprecationDate,
      isActive: true,
      isComplete: true,
      isCurrent: normalizedStatus === 'deprecated',
    })
  }

  return (
    <div className="relative">
      {/* Progress bar background */}
      <div className="absolute top-4 left-0 right-0 h-0.5 bg-ink-200" />

      {/* Active progress fill */}
      <div
        className="absolute top-4 left-0 h-0.5 bg-gradient-to-r from-status-beta via-status-optional to-status-released transition-all duration-500"
        style={{
          width: `${getProgressWidth(stages)}%`,
        }}
      />

      {/* Stages */}
      <div className="relative flex justify-between">
        {stages.map((stage, index) => (
          <div
            key={stage.key}
            className={`
              flex flex-col items-center
              ${index === 0 ? 'items-start' : index === stages.length - 1 ? 'items-end' : 'items-center'}
            `}
          >
            {/* Node */}
            <div
              className={`
                relative z-10 w-8 h-8 rounded-full flex items-center justify-center
                transition-all duration-300
                ${stage.isCurrent
                  ? 'bg-white border-2 border-accent-primary shadow-lg ring-4 ring-accent-primary/20'
                  : stage.isComplete
                    ? getStageColor(stage.key)
                    : stage.isActive
                      ? 'bg-white border-2 border-ink-300'
                      : 'bg-ink-100 border-2 border-ink-200'
                }
              `}
            >
              {stage.isComplete && !stage.isCurrent && (
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              )}
              {stage.isCurrent && (
                <div className="w-3 h-3 rounded-full bg-accent-primary animate-pulse-soft" />
              )}
            </div>

            {/* Label */}
            <div className={`
              mt-3 text-center
              ${index === 0 ? 'text-left' : index === stages.length - 1 ? 'text-right' : 'text-center'}
            `}>
              <p className={`
                text-xs font-medium uppercase tracking-wide
                ${stage.isCurrent
                  ? 'text-accent-primary'
                  : stage.isComplete || stage.isActive
                    ? 'text-ink-700'
                    : 'text-ink-400'
                }
              `}>
                {stage.label}
              </p>
              {stage.date && (
                <p className="mt-0.5 text-[10px] text-ink-500">
                  {formatDate(stage.date)}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getProgressWidth(stages: Stage[]): number {
  const activeIndex = stages.findIndex(s => s.isCurrent)
  if (activeIndex === -1) {
    // All complete
    const completeCount = stages.filter(s => s.isComplete).length
    return completeCount === stages.length ? 100 : (completeCount / (stages.length - 1)) * 100
  }
  if (activeIndex === 0) return 0
  return (activeIndex / (stages.length - 1)) * 100
}

function getStageColor(key: string): string {
  switch (key) {
    case 'announced':
      return 'bg-status-pending'
    case 'beta':
      return 'bg-status-beta'
    case 'production':
      return 'bg-status-optional'
    case 'released':
      return 'bg-status-released'
    case 'deprecated':
      return 'bg-status-deprecated'
    default:
      return 'bg-ink-400'
  }
}

function formatDate(dateStr: string): string {
  // Parse date parts directly to avoid timezone shift
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

// Skeleton for loading state
export function DeploymentTimelineSkeleton() {
  return (
    <div className="relative">
      <div className="absolute top-4 left-0 right-0 h-0.5 bg-ink-200" />
      <div className="relative flex justify-between">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex flex-col items-center">
            <div className="skeleton w-8 h-8 rounded-full" />
            <div className="mt-3 skeleton h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  )
}
